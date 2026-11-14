import sys

from fastembed import TextEmbedding

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EXPECTED_DIMENSION = 384

SAMPLE_SENTENCES = {
    "English": "What is Retrieval Augmented Generation?",
    "Hindi": "RAG क्या है और यह कैसे काम करता है?",
    "Punjabi": "RAG ਕੀ ਹੈ ਅਤੇ ਇਹ ਕਿਵੇਂ ਕੰਮ ਕਰਦਾ ਹੈ?",
}


def main():
    try:
        print(f"Loading model: {MODEL_NAME}...")
        model = TextEmbedding(model_name=MODEL_NAME)
        print("Model loaded successfully.\n")
    except Exception as exc:
        print(f"Error loading embedding model: {exc}", file=sys.stderr)
        return

    languages = list(SAMPLE_SENTENCES.keys())
    texts = list(SAMPLE_SENTENCES.values())

    try:
        print("Generating multilingual embeddings...")
        embeddings = list(model.embed(texts))
    except Exception as exc:
        print(f"Error generating embeddings: {exc}", file=sys.stderr)
        return

    all_valid = True
    for language, text, vector in zip(languages, texts, embeddings):
        dimension = len(vector)
        print(f"Language: {language}")
        print(f"Sentence: {text}")
        print(f"Embedding Dimension: {dimension}")

        if dimension != EXPECTED_DIMENSION:
            print(
                f"Validation Error: Expected {EXPECTED_DIMENSION} dimensions, got {dimension}.\n",
                file=sys.stderr,
            )
            all_valid = False
        else:
            print(f"Validation: Correct ({EXPECTED_DIMENSION} dimensions).\n")

    if all_valid:
        print("SUCCESS: All multilingual embeddings generated and verified with exactly 384 dimensions.")
    else:
        print("FAILURE: Embedding dimension check failed.", file=sys.stderr)


if __name__ == "__main__":
    main()

