from bankbot import rag

store = rag.build_index()          # downloads a ~80MB local embedding model on first run, takes a few minutes
for q in ["how long do I have to report a disputed charge",
          "what does an overseas card purchase cost extra",
          "lost card what do I do"]:
    print(q)
    for d in rag.search(store, q):
        print("   ", d.metadata["source"], "|", d.page_content[:60].replace("\n", " "))
