import os
import re
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient  # REQUIRED for MongoDBAtlasVectorSearch
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_huggingface import HuggingFaceEmbeddings
from .state import AgentState_1
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = "mongodb+srv://mathurkushagra163_db_user:ElTitz0clXuFXUeu@cluster0.1c2z3gd.mongodb.net/?appName=Cluster0"
DB_NAME = "hr_database"


async def retriever_node(state: AgentState_1):
    """
    Refined Retriever: Extracts IDs from query, resolves names via vector search,
    and fetches consolidated context from MongoDB.
    """

    embeddings = HuggingFaceEmbeddings(model_name="intfloat/e5-large-v2")

    # Async client (for lifecycle correctness)
    async_client = AsyncIOMotorClient(MONGO_URI)

    # Sync client REQUIRED for vector search
    sync_client = MongoClient(MONGO_URI)

    db = sync_client[DB_NAME]

    user_query = state["user_query"]
    emp_id = state.get("emp_id")

    if not emp_id:
        id_match = re.search(r"E\d+", user_query, re.IGNORECASE)

        if id_match:
            emp_id = id_match.group(0).upper()
            print(f"[+] Extracted ID from query: {emp_id}")

        else:
            print("[!] No ID in query. Searching for employee by name...")

            history_store = MongoDBAtlasVectorSearch(
                collection=db["employee_history"],
                embedding=embeddings,
                index_name="vector_index"
            )

            identity_results = history_store.similarity_search(
                f"query: {user_query}",
                k=1
            )

            if identity_results:
                emp_id = identity_results[0].metadata.get("emp_id")
                print(f"[+] Resolved identity via vector search: ID {emp_id}")

    employee_data = "No specific employee history found."

    if emp_id:
        history_store = MongoDBAtlasVectorSearch(
            collection=db["employee_history"],
            embedding=embeddings,
            index_name="vector_index"
        )

        history_docs = history_store.similarity_search(
            query=f"query: {user_query}",
            k=3,
            pre_filter={"emp_id": {"$eq": emp_id}}
        )

        employee_data = " | ".join(
            d.page_content.replace("passage: ", "") for d in history_docs
        )

    # Cleanup
    sync_client.close()
    async_client.close()

    return {
        "emp_id": emp_id,
        "employee_data": employee_data
    }


class MongoDBHRPipeline:
    """
    NOTE:
    This class MUST remain synchronous because
    MongoDBAtlasVectorSearch requires PyMongo collections.
    """

    def __init__(self, connection_string, db_name="hr_database"):
        self.client = MongoClient(connection_string)
        self.db = self.client[db_name]
        self.embeddings = HuggingFaceEmbeddings(
            model_name="intfloat/e5-large-v2"
        )
        self.vector_index_name = "vector_index"
        print("[+] Connected to MongoDB Atlas.")

    def fetch_top_policies(
        self,
        user_query: str,
        collection_name="policies",
        limit=6
    ):
        """
        Retrieves top policy chunks and returns a single formatted string
        containing content and file metadata for internal node consumption.
        """

        formatted_query = f"query: {user_query}"
        collection = self.db[collection_name]

        vector_store = MongoDBAtlasVectorSearch(
            collection=collection,
            embedding=self.embeddings,
            index_name=self.vector_index_name,
            relevance_score_fn="cosine"
        )

        results = vector_store.similarity_search(
            formatted_query,
            k=limit
        )

        if not results:
            return "NO RELEVANT POLICIES FOUND IN DATABASE."

        context_parts = [
            f"--- START OF RETRIEVED HR POLICIES (Query: {user_query}) ---"
        ]

        for i, doc in enumerate(results, 1):
            source_file = doc.metadata.get("source", "Unknown Document")
            page_num = doc.metadata.get("page", "N/A")

            section = (
                f"SECTION {i}\n"
                f"SOURCE: {source_file} (Page {page_num})\n"
                f"CONTENT:\n{doc.page_content}\n---"
            )
            context_parts.append(section)

        context_parts.append("--- END OF POLICY CONTEXT ---")

        return "\n\n".join(context_parts)
