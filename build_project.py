"""One command to rebuild everything:  python rebuild_all.py"""
import generate_products
import build_fts
import build_embeddings


def main():
    generate_products.main()   # 1. SQLite DB + 200 products
    build_fts.main()           # 2. FTS5 keyword index
    build_embeddings.main()    # 3. Embeddings + FAISS index
    print("\nDone. Created products.db and products.faiss")


if __name__ == "__main__":
    main()