import pandas as pd
from langchain_core.documents import Document
from tqdm import tqdm

from mcp_servers.core.settings import get_settings
from mcp_servers.core.db_manager import Database
from .retrievers import get_vectorstore
# from .retrievers.retrievers import get_vectorstore

settings = get_settings()

db_names = ["idog", "bioka", "biocode"]


def query_as_list(db, query):
    def flatten_list_comprehension(two_d_list):
        return [item for sublist in two_d_list for item in sublist]

    res = db.run(query)
    _r = res["data"].drop_duplicates().values.tolist()
    return flatten_list_comprehension(_r)


def add_hc_data(db, table, columns: list[str], vectorstore):
    for column in tqdm(columns, desc=table):
        res = query_as_list(db, f"SELECT {column} FROM {table}")
        for i in tqdm(range(len(res)), desc=f"Processing {column}"):
            res[i] = res[i].strip() if isinstance(res[i], str) else str(res[i])
            doc = Document(page_content=res[i], metadata={"table": table, "column": column})
            vectorstore.add_documents(documents=[doc])


def add_hc_data_batched(db, table, columns: list[str], vectorstore, chunk_size: int = 8):
    """
    Adds data from specified columns of a table to a vectorstore in batches.

    Args:
        db: Database connection/cursor object.
        table: Name of the table to query.
        columns: A list of column names to process.
        vectorstore: The vectorstore object with an add_documents method.
        chunk_size: The number of documents to add in each batch (default is 8).
    """
    for column in tqdm(columns, desc=f"Processing columns for table {table}"):
        # 假设 query_as_list 返回的是一个包含列值的列表，例如 [value1, value2, ...]
        # 如果它返回的是 [(value1,), (value2,)] 这样的元组列表，你需要调整 res_values 的处理
        res_values = query_as_list(db, f"SELECT {column} FROM {table}")

        if not res_values:
            print(f"No data found for column {column} in table {table}. Skipping.")
            continue

        # 以 chunk_size (8) 个一组处理 res_values
        # 使用 tqdm 包装 range 以显示批处理的进度
        for i in tqdm(
            range(0, len(res_values), chunk_size), desc=f"Batch processing {column} ({len(res_values)} items)"
        ):
            batch_values = res_values[i : i + chunk_size]
            documents_to_add = []

            for value in batch_values:
                # 处理每个值（去除字符串两端空格或转换为字符串）
                page_content = value.strip() if isinstance(value, str) else str(value)
                doc = Document(page_content=page_content, metadata={"table": table, "column": column})
                documents_to_add.append(doc)

            # 确保 documents_to_add 不为空
            if documents_to_add:
                vectorstore.add_documents(documents=documents_to_add)


for db_name in db_names:
    db = Database(settings.get_database_url(db_name), db_name)
    vectorstore = get_vectorstore(db_name)
    vectorstore.reset_collection()

    all_data = db.read_all()
    for table, data in tqdm(all_data.items(), desc=db_name):
        docs = [Document(page_content=d, metadata={"table": table}) for d in data]
        vectorstore.add_documents(documents=docs)


db = Database(settings.get_database_url("idog"), "idog")

vectorstore = get_vectorstore("idog_hc")
vectorstore.reset_collection()
add_hc_data(db, "breed", ["src_breed_name", "personality", "energy_level"], vectorstore)
add_hc_data(db, "general_disease_annotate", ["disease_name"], vectorstore)

db = Database(settings.get_database_url("bioka"), "bioka")

vectorstore = get_vectorstore("bioka_hc")
vectorstore.reset_collection()

add_hc_data(db, "overview", ["disease_name", "biomarker_name", "taxon_name"], vectorstore)


db = CommonDatabase(settings.get_database_url("biocode"), "biocode")

vectorstore = get_vectorstore("biocode_hc")
vectorstore.reset_collection()
add_hc_data(
    db,
    "tool_view",
    [
        "name",
        "category_name",
        "functional_category_name",
        "tool_type",
        "omics_name",
        "user_interface",
        "platform",
    ],
    vectorstore,
)

db = Database("mysql+pymysql://ewas_ai_sys:ewas_ai_sys123456@192.168.164.82:33060/ewas", "ewas")

vectorstore = get_vectorstore("ewas_hc")
vectorstore.reset_collection()
add_hc_data_batched(db, "trait_view", ["trait_name"], vectorstore)
add_hc_data_batched(db, "gene_view", ["gene_name"], vectorstore)


def add_qa_data(file_path: str, vectorstore_name: str):
    df = pd.read_csv(file_path)
    docs = []
    vectorstore = get_vectorstore(vectorstore_name)
    vectorstore.reset_collection()
    for row in tqdm(df.itertuples(index=False), desc=vectorstore_name):
        doc = Document(page_content=f"Question:{row.question}\nAnswer:{row.answer}")  # type: ignore
        docs.append(doc)
        vectorstore.add_documents(documents=docs)


# GSA
add_qa_data("data/raw_data/GSA/GSA-submission.csv", "gsa")

# GeneBase
add_qa_data("data/raw_data/GenBase/GenBase汇总QA.csv", "genebase")
retrived_docs = vectorstore.similarity_search("吸烟")
