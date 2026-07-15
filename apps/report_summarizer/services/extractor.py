import fitz


def extract_pdf_text(pdf_file):

    try:

        print("\nPDF RECEIVED:", pdf_file.name)

        pdf_bytes = pdf_file.read()

        doc = fitz.open(
            stream=pdf_bytes,
            filetype="pdf"
        )

        text = ""

        for page_num in range(len(doc)):

            page = doc.load_page(page_num)

            page_text = page.get_text("text")

            print(f"\nPAGE {page_num + 1}:\n")
            print(page_text[:300])

            text += page_text

        doc.close()

        print("\nFINAL TEXT:")
        print(text[:1000])

        return text.strip()

    except Exception as e:

        print("EXTRACT ERROR:", e)

        return ""