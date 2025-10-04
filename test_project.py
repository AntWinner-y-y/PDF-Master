import os
import sys
import pytest
from PyQt5.QtWidgets import QApplication
import fitz
from project import PDFApp, Config

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Prevent Qt from requiring a display for testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Test file path
TEST_PDF = "numbers.pdf"

# Fixture for QApplication instance
@pytest.fixture(scope="session")
def app():
    """Create a single QApplication instance for all tests"""
    app = QApplication.instance() or QApplication([])
    yield app
    app.processEvents()
    app.quit()

# Fixture for PDFApp instance
@pytest.fixture
def pdf_app(app, tmp_path):
    """Create a fresh PDFApp instance for each test"""
    # Initialize with proper cleanup handling
    pdf_app = PDFApp()
    pdf_app.show()
    pdf_app.output_dir = str(tmp_path)
    app.processEvents()

    yield pdf_app

    # Cleanup resources
    if hasattr(pdf_app, 'current_pdf') and pdf_app.current_pdf:
        pdf_app.current_pdf.close()
    pdf_app.close()
    pdf_app.deleteLater()
    app.processEvents()

# ============================================================================
# Viewer Tests
# ============================================================================

def test_pdf_loading(pdf_app):
    """Test PDF loading functionality"""
    pdf_app._load_and_display_pdf(TEST_PDF)
    assert pdf_app.current_pdf is not None
    assert pdf_app.current_page == 0
    assert pdf_app.zoom_factor == 1.0

def test_page_navigation(pdf_app):
    """Test page navigation functionality"""
    pdf_app._load_and_display_pdf(TEST_PDF)

    # Test next page
    initial_page = pdf_app.current_page
    pdf_app.next_page()
    assert pdf_app.current_page == initial_page + 1

    # Test previous page
    pdf_app.prev_page()
    assert pdf_app.current_page == initial_page

def test_zoom_operations(pdf_app):
    """Test zoom functionality"""
    pdf_app._load_and_display_pdf(TEST_PDF)
    initial_zoom = pdf_app.zoom_factor

    # Test zoom in
    pdf_app.zoom_view(1.2)
    assert pdf_app.zoom_factor > initial_zoom

    # Test zoom out
    pdf_app.zoom_view(0.8)
    assert pdf_app.zoom_factor < initial_zoom

# ============================================================================
# Split Tests
# ============================================================================

def test_split_page_switch(pdf_app):
    """Test switching to split mode"""
    pdf_app.stack_widget.setCurrentIndex(1)
    assert pdf_app.stack_widget.currentIndex() == 1

def test_split_functionality(pdf_app, tmp_path, monkeypatch):
    """Test PDF splitting with input validation"""
    # Load the test PDF
    pdf_app._load_and_display_pdf(TEST_PDF)
    assert pdf_app.current_pdf is not None, "PDF failed to load"

    # Mock QMessageBox.warning to capture warning message
    warning_messages = []
    def mock_warning(parent, title, message):
        warning_messages.append(message)
    monkeypatch.setattr('PyQt5.QtWidgets.QMessageBox.warning', mock_warning)

    # Test with invalid range
    pdf_app.split_input.setText("1-9")
    pdf_app.split_pdf()

    # Verify warning was displayed
    assert len(warning_messages) > 0
    assert any("valid page numbers" in msg.lower() for msg in warning_messages), \
           "Expected warning about invalid page numbers"

    # Verify no files were created in tmp_path
    files_created = [f for f in os.listdir(tmp_path) if f.endswith('.pdf')]
    assert len(files_created) == 0, "No PDF files should be created with invalid input"

# ============================================================================
# Merge Tests
# ============================================================================

def test_merge_page_switch(pdf_app):
    """Test switching to merge mode"""
    pdf_app.stack_widget.setCurrentIndex(2)
    assert pdf_app.stack_widget.currentIndex() == 2

def test_merge_list_operations(pdf_app):
    """Test merge list management"""
    # Add PDF to merge list
    pdf_app.merge_list.append(TEST_PDF)
    pdf_app.update_merge_table()
    assert len(pdf_app.merge_list) == 1

    # Remove PDF from merge list
    pdf_app.remove_from_merge(0)
    assert len(pdf_app.merge_list) == 0

def test_merge_functionality(pdf_app, tmp_path):
    """Test PDF merging functionality"""
    # Add test PDF twice to merge list
    pdf_app.merge_list = [TEST_PDF, TEST_PDF]

    # Create temporary output file
    output_file = str(tmp_path / "merged.pdf")

    try:
        # Perform merge operation
        output_pdf = fitz.open()
        for pdf_path in pdf_app.merge_list:
            pdf = fitz.open(pdf_path)
            output_pdf.insert_pdf(pdf)
            pdf.close()

        output_pdf.save(output_file)
        output_pdf.close()

        # Verify merged file was created
        assert os.path.exists(output_file)

    except Exception as e:
        pytest.fail(f"Merge operation failed: {str(e)}")

# ============================================================================
# Thumbnail Tests
# ============================================================================

def test_thumbnail_initialization(pdf_app):
    """Test thumbnail widget initialization"""
    pdf_app._load_and_display_pdf(TEST_PDF)
    assert pdf_app.thumbnail_widget is not None
    assert pdf_app.thumbnail_widget.thumbnail_width == Config.THUMBNAIL_DEFAULT_WIDTH

def test_thumbnail_size_adjustment(pdf_app):
    """Test thumbnail size adjustment functionality"""
    pdf_app._load_and_display_pdf(TEST_PDF)

    # Test increasing thumbnail size
    new_size = Config.THUMBNAIL_DEFAULT_WIDTH + 50
    pdf_app.thumbnail_widget.size_slider.setValue(new_size)
    assert pdf_app.thumbnail_widget.thumbnail_width == new_size
    assert pdf_app.thumbnail_widget.size_value_label.text() == f"{new_size}px"

def test_thumbnail_page_movement(pdf_app):
    """Test thumbnail page movement functionality"""
    pdf_app._load_and_display_pdf(TEST_PDF)

    # Get initial page contents
    page1_text = pdf_app.current_pdf[0].get_text().strip()
    page2_text = pdf_app.current_pdf[1].get_text().strip()

    # Test moving pages (swap page 1 and 2)
    pdf_app.thumbnail_widget.move_input.setText("1,2")
    pdf_app.thumbnail_widget.move_page()

    # Get page contents after move
    new_page1_text = pdf_app.current_pdf[0].get_text().strip()
    new_page2_text = pdf_app.current_pdf[1].get_text().strip()

    # Verify pages were actually swapped
    assert new_page1_text == page2_text, "First page should contain original second page content"
    assert new_page2_text == page1_text, "Second page should contain original first page content"

if __name__ == "__main__":
    pytest.main(["-v", __file__])
