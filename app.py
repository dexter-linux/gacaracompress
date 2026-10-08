import io
import fitz  # PyMuPDF
from PIL import Image
import docx
import streamlit as st

# Set page configuration
st.set_page_config(
    page_title="DocShrink Pro",
    page_icon="🗜️",
    layout="centered"
)

# -----------------------------------------------------------------------------
# Helper & Compression Functions
# -----------------------------------------------------------------------------

def format_size(size_bytes: int) -> str:
    """Converts bytes to human-readable format."""
    if size_bytes == 0:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if abs(size_bytes) < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

def compress_pdf(file_bytes: bytes, image_quality: int = 75, dpi: int = 130) -> bytes:
    """Compresses PDF files by re-rendering pages and compressing embedded images."""
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    new_doc = fitz.open()

    for page in doc:
        pix = page.get_pixmap(dpi=dpi)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        
        img_buffer = io.BytesIO()
        img.convert("RGB").save(img_buffer, format="JPEG", quality=image_quality, optimize=True)
        img_buffer.seek(0)

        rect = page.rect
        new_page = new_doc.new_page(width=rect.width, height=rect.height)
        new_page.insert_image(rect, stream=img_buffer.getvalue())

    output_buffer = io.BytesIO()
    new_doc.save(output_buffer, garbage=4, deflate=True, clean=True)
    new_doc.close()
    doc.close()
    return output_buffer.getvalue()

def compress_image(file_bytes: bytes, quality: int = 75, format_type: str = "JPEG") -> bytes:
    """Compresses images (PNG, JPG, WEBP) by adjusting compression quality."""
    img = Image.open(io.BytesIO(file_bytes))
    
    if format_type.upper() == "JPEG" and img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    output_buffer = io.BytesIO()
    img.save(output_buffer, format=format_type, quality=quality, optimize=True)
    return output_buffer.getvalue()

def compress_docx(file_bytes: bytes, image_quality: int = 75) -> bytes:
    """Compresses DOCX files by re-encoding internal images."""
    doc = docx.Document(io.BytesIO(file_bytes))
    
    for rel in doc.part.rels.values():
        if "image" in rel.target_ref:
            img_part = rel.target_part
            try:
                img = Image.open(io.BytesIO(img_part.blob))
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=image_quality, optimize=True)
                img_part._blob = buffer.getvalue()
            except Exception:
                continue

    output_buffer = io.BytesIO()
    doc.save(output_buffer)
    return output_buffer.getvalue()


# -----------------------------------------------------------------------------
# Streamlit UI
# -----------------------------------------------------------------------------

st.title("🗜️ DocShrink Pro")
st.caption("Compress PDFs, Images, and DOCX files entirely in-memory.")

st.divider()

# Sidebar Controls
st.sidebar.header("⚙️ Compression Settings")
quality = st.sidebar.slider(
    "Image Quality", 
    min_value=10, 
    max_value=90, 
    value=65, 
    step=5,
    help="Lower values produce smaller files but decrease visual quality."
)

pdf_dpi = st.sidebar.slider(
    "PDF Rendering Resolution (DPI)", 
    min_value=72, 
    max_value=300, 
    value=130, 
    step=10,
    help="Lower resolution significantly reduces PDF file size."
)

# File Uploader
uploaded_file = st.file_uploader(
    "Upload a file to compress",
    type=["pdf", "png", "jpg", "jpeg", "webp", "docx"],
    help="Supported formats: PDF, PNG, JPG, WEBP, DOCX"
)

if uploaded_file is not None:
    original_bytes = uploaded_file.getvalue()
    original_size = len(original_bytes)
    file_name = uploaded_file.name
    file_ext = file_name.split(".")[-1].lower()

    # Display Input Info
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"**Filename:** {file_name}")
    with col2:
        st.info(f"**Original Size:** {format_size(original_size)}")

    st.divider()

    # Compress Action
    if st.button("Start Compression", type="primary", use_container_width=True):
        with st.spinner("Compressing your file..."):
            try:
                compressed_bytes = None

                if file_ext == "pdf":
                    compressed_bytes = compress_pdf(original_bytes, image_quality=quality, dpi=pdf_dpi)
                elif file_ext in ["jpg", "jpeg", "png", "webp"]:
                    fmt = "PNG" if file_ext == "png" else "JPEG"
                    compressed_bytes = compress_image(original_bytes, quality=quality, format_type=fmt)
                elif file_ext == "docx":
                    compressed_bytes = compress_docx(original_bytes, image_quality=quality)

                if compressed_bytes:
                    compressed_size = len(compressed_bytes)
                    saved_bytes = original_size - compressed_size
                    ratio = (saved_bytes / original_size) * 100 if original_size > 0 else 0

                    st.success("Compression Complete!")
                    m1, m2, m3 = st.columns(3)
                    m1.metric("New Size", format_size(compressed_size))
                    m2.metric("Space Saved", format_size(max(0, saved_bytes)))
                    m3.metric("Reduction", f"{ratio:.1f}%" if ratio > 0 else "0%")

                    st.download_button(
                        label="⬇️ Download Compressed File",
                        data=compressed_bytes,
                        file_name=f"compressed_{file_name}",
                        mime=uploaded_file.type,
                        use_container_width=True
                    )
            except Exception as e:
                st.error(f"An error occurred during compression: {str(e)}")

st.divider()
st.markdown(
    "<div style='text-align: center; color: #64748B; font-size: 0.85rem;'>"
    "DocShrink Pro • Processed in-memory • Zero data retention"
    "</div>",
    unsafe_allow_html=True
)
