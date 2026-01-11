import os
import pandas as pd
from pymongo import MongoClient
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

class MongoDBHRPipeline:
    def __init__(self, connection_string, db_name="hr_database"):
        self.client = MongoClient(connection_string)
        self.db_name = db_name
        self.embeddings = HuggingFaceEmbeddings(model_name="intfloat/e5-large-v2")
        print("[+] Connected to MongoDB Atlas.")

    def process_and_upload_pdfs(self, directory_path, collection_name="policies"):
        """Processes office PDFs into the policy collection."""
        if not os.path.exists(directory_path):
            print(f"[!] Error: Path {directory_path} not found.")
            return

        loader = DirectoryLoader(directory_path, glob="**/*.pdf", loader_cls=PyPDFLoader)
        raw_docs = loader.load()
        
        splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
        chunks = splitter.split_documents(raw_docs)

        for chunk in chunks:
            chunk.page_content = f"passage: {chunk.page_content}"
            chunk.metadata["source_type"] = "POLICY"

        collection = self.client[self.db_name][collection_name]
        MongoDBAtlasVectorSearch.from_documents(
            documents=chunks,
            embedding=self.embeddings,
            collection=collection,
            index_name="vector_index" # Must match the name you gave in Atlas UI
        )
        print(f"[+] Uploaded {len(chunks)} policy chunks to MongoDB.")

    def process_and_upload_employee_csv(self, file_path, collection_name="employee_history"):
        """Groups CSV data and uploads consolidated summaries to MongoDB."""
        if not os.path.exists(file_path):
            print(f"[!] Error: CSV {file_path} not found.")
            return

        df = pd.read_csv(file_path)
        grouped = df.groupby(['emp_id', 'name', 'dept'])
        consolidated_docs = []

        for (emp_id, name, dept), group in grouped:
            daily_logs = [
                f"{row['day']}: {row['attendance_pct']}% Att, {row['screen_time_hours']}hrs Screen, Score: {row['task_completion_score']}"
                for _, row in group.iterrows()
            ]
            
            manager_comments = " ".join(group['manager_comment_hint'].unique())

            full_text = (
                f"passage: Weekly Performance Summary for {name} (ID: {emp_id}). "
                f"Department: {dept}. Weekly Logs: {' | '.join(daily_logs)}. "
                f"Manager Notes: {manager_comments}"
            )

            doc = Document(
                page_content=full_text,
                metadata={
                    "emp_id": str(emp_id),
                    "name": name,
                    "dept": dept,
                    "source_type": "EMPLOYEE_SUMMARY"
                }
            )
            consolidated_docs.append(doc)

        collection = self.client[self.db_name][collection_name]
        MongoDBAtlasVectorSearch.from_documents(
            documents=consolidated_docs,
            embedding=self.embeddings,
            collection=collection,
            index_name="vector_index"
        )
        print(f"[+] Uploaded {len(consolidated_docs)} employee summaries to MongoDB.")

# --- EXECUTION ---
if __name__ == "__main__":
    MONGO_URI = os.environ.get("MONGO_URI")
    
    pipeline = MongoDBHRPipeline(MONGO_URI)

    pipeline.process_and_upload_pdfs(r"Data\Office Data")

    pipeline.process_and_upload_employee_csv(r"Data\Employee Data\employee_weekly_progress.csv")