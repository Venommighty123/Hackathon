import os
import pandas as pd
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

class MetadataAwarePipeline:
    def __init__(self):
        # E5-large-v2 is an asymmetric model. Passages need "passage: " and queries need "query: "
        self.embeddings = HuggingFaceEmbeddings(model_name="intfloat/e5-large-v2")
        self.documents = []

    def load_office_pdfs(self, directory_path):
        """Loads all PDFs from the office_data folder and adds E5 prefixes."""
        if not os.path.exists(directory_path):
            print(f"[!] Error: Office directory not found at {directory_path}")
            return

        print(f"[*] Loading PDFs from {directory_path}...")
        loader = DirectoryLoader(directory_path, glob="**/*.pdf", loader_cls=PyPDFLoader)
        raw_docs = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800, 
            chunk_overlap=100
        )
        chunks = text_splitter.split_documents(raw_docs)

        for chunk in chunks:
            chunk.page_content = f"passage: {chunk.page_content}"
            chunk.metadata["source_type"] = "POLICY"
            self.documents.append(chunk)
        print(f"[+] Loaded {len(chunks)} policy chunks.")

    def load_employee_csv(self, file_path):
        """
        Groups CSV data by employee and creates a single consolidated 
        performance summary document for each person.
        """
        if not os.path.exists(file_path):
            print(f"[!] Error: CSV file not found at {file_path}")
            return

        print(f"[*] Grouping and loading employee data from {file_path}...")
        df = pd.read_csv(file_path)

        grouped = df.groupby(['emp_id', 'name', 'dept'])

        records_added = 0
        for (emp_id, name, dept), group in grouped:
            daily_logs = []
            for _, row in group.iterrows():
                log = (f"On {row['day']}: {row['attendance_pct']}% attendance, "
                       f"{row['screen_time_hours']} hrs screen time, "
                       f"Task Score: {row['task_completion_score']}.")
                daily_logs.append(log)

            comments = " ".join(group['manager_comment_hint'].unique())

            consolidated_text = (
                f"Weekly Performance Summary for {name} (ID: {emp_id}) - {dept} Department.\n"
                "Daily Records:\n" + "\n".join(daily_logs) + 
                f"\nOverall Manager Feedback: {comments}"
            )

            self.documents.append(Document(
                page_content=f"passage: {consolidated_text}",
                metadata={
                    "source_type": "EMPLOYEE_SUMMARY",
                    "emp_id": str(emp_id),
                    "dept": dept,
                    "record_count": len(group)
                }
            ))
            records_added += 1

        print(f"[+] Created {records_added} consolidated employee summaries.")

    def save_index(self, index_name="hr_vector_db"):
        if not self.documents:
            print("[!] No documents to save. Load data first.")
            return
        
        vector_db = FAISS.from_documents(self.documents, self.embeddings)
        vector_db.save_local(index_name)
        print(f"[+] FAISS Index saved to {index_name}")
        self.documents = []

if __name__ == "__main__":
    pipe = MetadataAwarePipeline()

    pipe.load_office_pdfs(r"Data\Office Data")
    pipe.save_index(r"vector databases\hr_vector_db")

    pipe.load_employee_csv(r"Data\Employee Data\employee_weekly_progress.csv")
    pipe.save_index(r"vector databases\employee_history_db")