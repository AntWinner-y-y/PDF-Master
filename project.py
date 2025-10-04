import os
import sys
import fitz
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QFileDialog, QLabel, QLineEdit, QScrollArea, QMessageBox, QTableWidget,
    QTableWidgetItem, QStackedWidget, QSlider, QSplitter, QFrame
)
from PyQt5.QtGui import QImage, QPixmap, QFont, QIcon
from PyQt5.QtCore import Qt

# ============================================================================
# Constants and Configuration
# ============================================================================

class Config:
    """configuration settings"""

    # Window Settings
    WINDOW_SIZE = (960, 720)
    DEFAULT_FONT_SIZE = 11
    DEFAULT_BUTTON_HEIGHT = 36

    # Zoom Settings
    ZOOM_LIMITS = (0.1, 5.0)
    ZOOM_STEP = 1.2

    # Widget Dimensions
    BUTTON_WIDTHS = {
        "navigation": 40,
        "page_input": 100,
        "zoom_label": 90,
    }

    # Thumbnail Settings
    THUMBNAIL_MIN_WIDTH = 100
    THUMBNAIL_MAX_WIDTH = 300
    THUMBNAIL_DEFAULT_WIDTH = 100
    THUMBNAIL_MIN_HEIGHT = 100
    THUMBNAIL_SPACING = 10

    # File Settings
    PDF_MAGIC_NUMBER = b"%PDF"
    PDF_FILTER = "PDF files (*.pdf)"

# ============================================================================
# Thumbnail Widget Component
# ============================================================================

class ThumbnailWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.thumbnail_width = Config.THUMBNAIL_DEFAULT_WIDTH
        self.initUI()

    def initUI(self):
        # Main layout
        layout = QVBoxLayout()
        layout.setSpacing(5)
        self.setLayout(layout)

        # Add page movement controls
        move_layout = QHBoxLayout()
        move_label = QLabel("Move page: ")
        font = move_label.font()
        font.setPointSize(11)
        move_label.setFont(font)
        self.move_input = QLineEdit()
        self.move_input.setPlaceholderText("e.g. 2,3")
        self.move_input.setFixedWidth(100)
        font = self.move_input.font()
        font.setPointSize(11)
        self.move_input.setFont(font)
        self.move_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        move_btn = QPushButton("Move")
        move_btn.setMinimumHeight(36)
        font = move_btn.font()
        font.setPointSize(11)
        move_btn.setFont(font)
        move_btn.clicked.connect(self.move_page)
        move_layout.addWidget(move_label)
        move_layout.addWidget(self.move_input)
        move_layout.addWidget(move_btn)
        move_layout.addStretch()
        layout.addLayout(move_layout)

        # Add size control with slider
        size_layout = QHBoxLayout()
        size_label = QLabel("Size: ")
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(Config.THUMBNAIL_MIN_WIDTH, Config.THUMBNAIL_MAX_WIDTH)
        self.size_slider.setValue(self.thumbnail_width)
        self.size_slider.setTickPosition(QSlider.TicksBelow)
        self.size_slider.setTickInterval(50)
        self.size_slider.valueChanged.connect(self.update_thumbnail_size)

        # Add size value label
        self.size_value_label = QLabel(f"{self.thumbnail_width}px")
        self.size_value_label.setMinimumWidth(50)
        self.size_value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # Style the slider
        self.size_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #999999;
                height: 8px;
                background: #ffffff;
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #5c5c5c;
                border: 1px solid #5c5c5c;
                width: 18px;
                margin: -6px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background: #404040;
            }
        """)

        size_layout.addWidget(size_label)
        size_layout.addWidget(self.size_slider)
        size_layout.addWidget(self.size_value_label)
        layout.addLayout(size_layout)

        # Scroll area for thumbnails
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Container for thumbnails
        self.thumbnail_container = QWidget()
        self.thumbnail_layout = QVBoxLayout()
        self.thumbnail_layout.setSpacing(Config.THUMBNAIL_SPACING)
        self.thumbnail_layout.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self.thumbnail_container.setLayout(self.thumbnail_layout)

        scroll.setWidget(self.thumbnail_container)
        layout.addWidget(scroll)

        # Set frame style
        scroll.setFrameStyle(QFrame.StyledPanel)

        # Set size constraints
        self.setMinimumWidth(Config.THUMBNAIL_MIN_WIDTH - 20)
        self.setMaximumWidth(Config.THUMBNAIL_MAX_WIDTH + 20)

        # Add resize handle style
        self.setStyleSheet("""
            QWidget {
                border-right: 1px solid #999;
                background-color: #f5f5f5;
            }
        """)

    def update_thumbnail_size(self, width):
        """Update the size of all thumbnails"""
        self.thumbnail_width = width
        self.size_value_label.setText(f"{width}px")
        if hasattr(self.parent, 'current_pdf') and self.parent.current_pdf:
            self.load_thumbnails(self.parent.current_pdf)

    def load_thumbnails(self, pdf):
        """Load thumbnails for all pages"""
        # Clear existing thumbnails
        for i in reversed(range(self.thumbnail_layout.count())):
            self.thumbnail_layout.itemAt(i).widget().deleteLater()

        if not pdf:
            return

        # Create thumbnails for each page
        for page_num in range(len(pdf)):
            # Create frame for thumbnail
            frame = QFrame()
            frame.setFrameStyle(QFrame.StyledPanel)
            frame_layout = QVBoxLayout()
            frame.setLayout(frame_layout)

            # Create thumbnail label
            thumb_label = QLabel()
            thumb_label.setAlignment(Qt.AlignCenter)

            # Create editable page number field
            page_num_layout = QHBoxLayout()
            page_label = QLabel("Page")
            page_num_input = QLineEdit(str(page_num + 1))
            page_num_input.setFixedWidth(40)
            page_num_input.setAlignment(Qt.AlignCenter)

            # Add page label and number display (non-editable for now)
            page_num_layout.addWidget(page_label)
            page_num_layout.addWidget(page_num_input)
            page_num_layout.setAlignment(Qt.AlignCenter)
            page_num_input.setReadOnly(True)  # Make it read-only until we implement proper page moving

            # Get page and create thumbnail
            page = pdf[page_num]
            matrix = fitz.Matrix(self.thumbnail_width/page.rect.width,
                               self.thumbnail_width/page.rect.width)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            img = QImage(pix.samples, pix.width, pix.height, pix.stride,
                        QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(img)

            # Set thumbnail
            thumb_label.setPixmap(pixmap)
            frame_layout.addWidget(thumb_label)
            frame_layout.addLayout(page_num_layout)

            # Make thumbnail clickable
            thumb_label.mousePressEvent = lambda e, num=page_num: self.thumbnail_clicked(e, num)
            frame.mousePressEvent = lambda e, num=page_num: self.thumbnail_clicked(e, num)

            self.thumbnail_layout.addWidget(frame)

    def thumbnail_clicked(self, event=None, page_num=None):
        """Handle thumbnail click"""
        # Ensure we have a valid page number (may come from event or direct call)
        if isinstance(page_num, int) and self.parent.current_pdf:
            # self.parent.add_to_history(self.parent.current_page)  # Add current page to history before changing
            self.parent.current_page = page_num
            self.parent.display_page()

    def move_page(self):
        """Move a page to a new position and shift other pages accordingly"""
        if not self.parent.current_pdf:
            QMessageBox.warning(self, "Warning", "Please open a PDF first")
            return

        try:
            # Parse input format (source,target)
            text = self.move_input.text().strip()

            # Extract source and target page numbers
            nums = text.split(",")
            if len(nums) != 2:
                raise ValueError("Invalid format")

            source = int(nums[0]) - 1  # Convert to 0-based index
            target = int(nums[1]) - 1

            # Validate page numbers
            if source < 0 or source >= len(self.parent.current_pdf) or target < 0 or target >= len(self.parent.current_pdf):
                raise ValueError("Invalid page numbers")

            if source == target:
                return

            try:
                # Create a new PDF with reordered pages
                new_pdf = fitz.open()

                # If moving forward (e.g., 1 to 8)
                if target > source:
                    # Copy pages before source
                    for i in range(source):
                        new_pdf.insert_pdf(self.parent.current_pdf, from_page=i, to_page=i)

                    # Copy pages between source and target, shifting up
                    for i in range(source, target):
                        new_pdf.insert_pdf(self.parent.current_pdf, from_page=i+1, to_page=i+1)

                    # Insert source page at target position
                    new_pdf.insert_pdf(self.parent.current_pdf, from_page=source, to_page=source)

                    # Copy remaining pages
                    for i in range(target+1, len(self.parent.current_pdf)):
                        new_pdf.insert_pdf(self.parent.current_pdf, from_page=i, to_page=i)

                # If moving backward (e.g., 8 to 1)
                else:
                    # Copy pages before target
                    for i in range(target):
                        new_pdf.insert_pdf(self.parent.current_pdf, from_page=i, to_page=i)

                    # Insert source page at target position
                    new_pdf.insert_pdf(self.parent.current_pdf, from_page=source, to_page=source)

                    # Copy pages between target and source, shifting down
                    for i in range(target, source):
                        new_pdf.insert_pdf(self.parent.current_pdf, from_page=i, to_page=i)

                    # Copy remaining pages
                    for i in range(source+1, len(self.parent.current_pdf)):
                        new_pdf.insert_pdf(self.parent.current_pdf, from_page=i, to_page=i)

                # Save to a temporary file
                temp_path = self.parent.current_pdf.name + ".temp"
                new_pdf.save(temp_path)
                new_pdf.close()

                # Close current PDF and replace with new one
                self.parent.current_pdf.close()
                os.replace(temp_path, self.parent.current_pdf.name)

                # Reload the PDF
                self.parent.current_pdf = fitz.open(self.parent.current_pdf.name)
                self.parent.display_page()
                self.load_thumbnails(self.parent.current_pdf)

                # Add move to history
                self.parent.add_to_move_history(source, target)

                # Clear the move input
                self.move_input.clear()

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error moving pages: {str(e)}")

        except ValueError:
            QMessageBox.warning(self, "Warning", "Please use format: source,target (e.g., 2,3)")
            return

# ============================================================================
# Main app
# ============================================================================

class PDFApp(QMainWindow):
    """Main application window for PDF viewing, merging and splitting operations"""

    # == UI Setup Helpers ================================================================================================================================
    def _setup_button(self, button, font_size=11, width=None, height=36):
        """Configure button appearance and size"""
        if width:
            button.setFixedWidth(width)
        button.setMinimumHeight(height)
        font = button.font()
        font.setPointSize(font_size)
        button.setFont(font)
        return button

    def _set_font(self, widget, size=11):
        """Helper method to set font for widgets"""
        font = widget.font()
        font.setPointSize(size)
        widget.setFont(font)
        return widget

    def _add_navigation_to_layout(self, layout, prev_btn, page_label, page_input, total_pages_label, next_btn):
        """Helper method to add navigation controls to layout"""
        layout.addWidget(prev_btn)
        layout.addWidget(page_label)
        layout.addWidget(page_input)
        layout.addWidget(total_pages_label)
        layout.addWidget(next_btn)

    def _add_zoom_to_layout(self, layout, zoom_out_btn, zoom_label, zoom_in_btn):
        """Add zoom control widgets to layout"""
        layout.addWidget(zoom_out_btn)
        layout.addWidget(zoom_label)
        layout.addWidget(zoom_in_btn)

    # == Initialization ================================================================================================================================
    def __init__(self):
        """Initialize application window and setup UI"""
        super().__init__()
        self._init_state()
        self._setup_window()
        self._setup_application_font()
        self.initUI()

    def _init_state(self):
        """Initialize state variables"""
        self.current_pdf = None
        self.current_page = None
        self.zoom_factor = 1.0
        self.merge_list = []
        self.move_history = []  # Store history of page moves (source, target)
        self.history_index = -1  # Current position in history
        self.setFocusPolicy(Qt.StrongFocus)

    def _setup_window(self):
        """Set up window properties and icon"""
        self.setWindowTitle("PDF Master")
        self.setGeometry(100, 100, *Config.WINDOW_SIZE)
        self._load_window_icon()

    def _load_window_icon(self):
        """Load and set window icon"""
        try:
            app_icon = QIcon("icon.ico")
            self.setWindowIcon(app_icon)
        except Exception as e:
            print(f"Warning: Could not load window icon: {e}")

    def _setup_application_font(self):
        """Set up default application font"""
        font = QFont()
        font.setPointSize(Config.DEFAULT_FONT_SIZE - 1)
        QApplication.setFont(font)

    def add_to_move_history(self, source, target):
        """Add a page move operation to history"""
        # Remove any future history if we're not at the end
        if self.history_index < len(self.move_history) - 1:
            self.move_history = self.move_history[:self.history_index + 1]

        # Add the new move to history
        self.move_history.append((source, target))
        self.history_index = len(self.move_history) - 1

    def undo_page(self):
        """Undo the last page move operation"""
        if not self.current_pdf or self.history_index < 0:
            return

        try:
            source, target = self.move_history[self.history_index]
            # When undoing, we move from target back to source
            self._move_page(target + 1, source + 1)  # Adding 1 because move_page expects 1-based indices
            self.history_index -= 1
            # Don't add this reverse move to history since it's an undo operation
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error undoing page move: {str(e)}")

    def redo_page(self):
        """Redo the last undone page move operation"""
        if not self.current_pdf or self.history_index >= len(self.move_history) - 1:
            return

        try:
            self.history_index += 1
            source, target = self.move_history[self.history_index]
            # When redoing, we move from source to target again
            self._move_page(source + 1, target + 1)  # Adding 1 because move_page expects 1-based indices
            # Don't add this move to history since it's a redo operation
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error redoing page move: {str(e)}")

    def _move_page(self, source, target):
        """Helper method to move a page without adding to history"""
        try:
            # Create a new PDF with reordered pages
            new_pdf = fitz.open()
            source = source - 1  # Convert to 0-based index
            target = target - 1

            # If moving forward (e.g., 1 to 8)
            if target > source:
                # Copy pages before source
                for i in range(source):
                    new_pdf.insert_pdf(self.current_pdf, from_page=i, to_page=i)

                # Copy pages between source and target, shifting up
                for i in range(source, target):
                    new_pdf.insert_pdf(self.current_pdf, from_page=i+1, to_page=i+1)

                # Insert source page at target position
                new_pdf.insert_pdf(self.current_pdf, from_page=source, to_page=source)

                # Copy remaining pages
                for i in range(target+1, len(self.current_pdf)):
                    new_pdf.insert_pdf(self.current_pdf, from_page=i, to_page=i)

            # If moving backward (e.g., 8 to 1)
            else:
                # Copy pages before target
                for i in range(target):
                    new_pdf.insert_pdf(self.current_pdf, from_page=i, to_page=i)

                # Insert source page at target position
                new_pdf.insert_pdf(self.current_pdf, from_page=source, to_page=source)

                # Copy pages between target and source, shifting down
                for i in range(target, source):
                    new_pdf.insert_pdf(self.current_pdf, from_page=i, to_page=i)

                # Copy remaining pages
                for i in range(source+1, len(self.current_pdf)):
                    new_pdf.insert_pdf(self.current_pdf, from_page=i, to_page=i)

            # Save to a temporary file
            temp_path = self.current_pdf.name + ".temp"
            new_pdf.save(temp_path)
            new_pdf.close()

            # Close current PDF and replace with new one
            self.current_pdf.close()
            os.replace(temp_path, self.current_pdf.name)

            # Reload the PDF
            self.current_pdf = fitz.open(self.current_pdf.name)
            self.display_page()
            self.thumbnail_widget.load_thumbnails(self.current_pdf)

        except Exception as e:
            raise Exception(f"Error moving page: {str(e)}")

    def initUI(self):
        """Initialize the user interface"""
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout()
        main_widget.setLayout(layout)

        # Mode selection buttons
        mode_layout = QHBoxLayout()
        mode_layout.setSpacing(20)
        viewer_btn = QPushButton("Viewer")
        merge_btn = QPushButton("Merge PDFs")
        split_btn = QPushButton("Split PDF")

        # Set size for mode buttons
        for btn in [viewer_btn, merge_btn, split_btn]:
            btn.setMinimumHeight(40)
            font = btn.font()
            font.setPointSize(11)
            btn.setFont(font)
        viewer_btn.clicked.connect(lambda: self.stack_widget.setCurrentIndex(0))
        split_btn.clicked.connect(lambda: self.stack_widget.setCurrentIndex(1))
        merge_btn.clicked.connect(lambda: self.stack_widget.setCurrentIndex(2))
        mode_layout.addWidget(viewer_btn)
        mode_layout.addWidget(split_btn)
        mode_layout.addWidget(merge_btn)
        layout.addLayout(mode_layout)

        # Create stacked widget for different modes
        self.stack_widget = QStackedWidget()
        self.stack_widget.addWidget(self.create_viewer_page())
        self.stack_widget.addWidget(self.create_split_page())
        self.stack_widget.addWidget(self.create_merge_page())
        layout.addWidget(self.stack_widget)

    # == Viewer page ================================================================================================================================
    def create_viewer_page(self):
        """Create the viewer page with PDF viewing functionality"""
        viewer_page = QWidget()
        viewer_layout = QVBoxLayout()
        viewer_page.setLayout(viewer_layout)

        # Viewer buttons and zoom controls
        button_layout = QHBoxLayout()

        # Open/Close buttons
        open_btn = self._setup_button(QPushButton("Open PDF"))
        close_btn = self._setup_button(QPushButton("Close PDF"))

        # Navigation controls
        prev_btn, next_btn, page_label, self.page_input, self.total_pages_label = self._create_navigation_controls()

        # Zoom controls
        zoom_out_btn, self.zoom_label, zoom_in_btn = self._create_zoom_controls()

        # Connect events
        self.zoom_label.editingFinished.connect(lambda: self.update_zoom_from_input(self.zoom_label.text()))
        open_btn.clicked.connect(self.open_pdf)
        close_btn.clicked.connect(self.close_pdf)
        zoom_in_btn.clicked.connect(lambda: self.zoom_view(1.2))
        zoom_out_btn.clicked.connect(lambda: self.zoom_view(0.8))

        # Create undo/redo buttons
        undo_btn = self._setup_button(QPushButton("↶"), width=40)
        redo_btn = self._setup_button(QPushButton("↷"), width=40)
        undo_btn.setToolTip("Undo last page change")
        redo_btn.setToolTip("Redo last page change")
        undo_btn.clicked.connect(self.undo_page)
        redo_btn.clicked.connect(self.redo_page)

        # Arrange controls in layout
        button_layout.addWidget(open_btn)
        button_layout.addWidget(close_btn)
        button_layout.addStretch()
        button_layout.addWidget(undo_btn)
        button_layout.addWidget(redo_btn)
        button_layout.addSpacing(10)
        self._add_navigation_to_layout(button_layout, prev_btn, page_label, self.page_input,
                                     self.total_pages_label, next_btn)
        button_layout.addStretch()
        self._add_zoom_to_layout(button_layout, zoom_out_btn, self.zoom_label, zoom_in_btn)

        viewer_layout.addLayout(button_layout)

        # Create splitter for thumbnails and main view
        splitter = QSplitter(Qt.Horizontal)

        # Set splitter properties for better visibility and handling
        splitter.setHandleWidth(8)  # Make the handle wider and easier to grab
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #ccc;
                border: 1px solid #999;
            }
            QSplitter::handle:hover {
                background-color: #999;
            }
        """)

        # Create thumbnail panel
        self.thumbnail_widget = ThumbnailWidget(self)
        splitter.addWidget(self.thumbnail_widget)

        # Create PDF display area
        main_scroll = QScrollArea()
        main_scroll.setWidgetResizable(True)
        pdf_label = QLabel()
        pdf_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_scroll.setWidget(pdf_label)
        splitter.addWidget(main_scroll)

        # Set initial splitter sizes and behavior
        splitter.setSizes([270, self.width() - 270])

        # Make splitter handle interactive
        splitter.setChildrenCollapsible(False)  # Prevent widgets from being collapsed to zero size
        splitter.setOpaqueResize(True)  # Real-time resize feedback

        # Store splitter reference
        self.viewer_splitter = splitter

        # Store references
        self.scroll = main_scroll
        self.pdf_label = pdf_label

        # Add zoom functionality
        main_scroll.wheelEvent = self.handle_zoom

        # Add splitter to viewer layout
        viewer_layout.addWidget(splitter)

        return viewer_page

    def _create_navigation_controls(self):
        """Create navigation controls (prev, next, page input)"""
        prev_btn = self._setup_button(QPushButton("←"), width=40)
        next_btn = self._setup_button(QPushButton("→"), width=40)
        page_label = self._set_font(QLabel("Page:"))
        page_input = QLineEdit()
        page_input.setFixedWidth(100)
        self._set_font(page_input)
        page_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        total_pages_label = self._set_font(QLabel("/ 0"))

        prev_btn.clicked.connect(self.prev_page)
        next_btn.clicked.connect(self.next_page)
        page_input.editingFinished.connect(self.go_to_page)

        return prev_btn, next_btn, page_label, page_input, total_pages_label

    def _create_zoom_controls(self):
        """Create zoom control buttons and label"""
        zoom_out_btn = self._setup_button(QPushButton("-"), font_size=14, width=40)
        zoom_label = QLineEdit("100%")
        zoom_label.setFixedWidth(90)
        self._set_font(zoom_label, 12)
        zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        zoom_in_btn = self._setup_button(QPushButton("+"), font_size=14, width=40)

        return zoom_out_btn, zoom_label, zoom_in_btn

    # == split page ================================================================================================================================
    def create_split_page(self):
        """Create the split page with PDF splitting functionality"""
        # Create split page
        split_page = QWidget()
        split_layout = QVBoxLayout()
        split_page.setLayout(split_layout)

        # Add controls layout
        button_layout = QHBoxLayout()

        # Open/Close controls
        open_btn = self._setup_button(QPushButton("Open PDF"))
        close_btn = self._setup_button(QPushButton("Close PDF"))
        open_btn.clicked.connect(self.open_pdf)
        close_btn.clicked.connect(self.close_pdf)

        # Navigation controls
        prev_btn, next_btn, page_label, page_input, total_pages_label = self._create_navigation_controls()

        # Zoom controls
        zoom_out_btn, zoom_label, zoom_in_btn = self._create_zoom_controls()

        # Store references to split page controls
        self.split_page_input = page_input
        self.split_total_pages_label = total_pages_label
        self.split_zoom_label = zoom_label

        # Connect events
        zoom_label.editingFinished.connect(lambda: self.update_zoom_from_input(zoom_label.text()))
        zoom_in_btn.clicked.connect(lambda: self.zoom_view(1.2))
        zoom_out_btn.clicked.connect(lambda: self.zoom_view(0.8))

        # Add all controls to layout using helper methods
        button_layout.addWidget(open_btn)
        button_layout.addWidget(close_btn)
        button_layout.addStretch()
        self._add_navigation_to_layout(button_layout, prev_btn, page_label, page_input,
                                     total_pages_label, next_btn)
        button_layout.addStretch()
        self._add_zoom_to_layout(button_layout, zoom_out_btn, zoom_label, zoom_in_btn)
        split_layout.addLayout(button_layout)

        # Add split controls
        split_controls = QHBoxLayout()
        split_label = QLabel("Split at pages:")
        font = split_label.font()
        font.setPointSize(11)
        split_label.setFont(font)
        self.split_input = QLineEdit()
        self.split_input.setFixedWidth(280)
        self.split_input.setPlaceholderText("e.g., 1,4;2-3;5-6")
        self.split_input.setMinimumHeight(36)
        font = self.split_input.font()
        font.setPointSize(11)
        self.split_input.setFont(font)
        split_btn = QPushButton("Split PDF")
        font = split_btn.font()
        font.setPointSize(11)
        split_btn.setFont(font)
        split_btn.clicked.connect(self.split_pdf)
        split_controls.addWidget(split_label)
        split_controls.addWidget(self.split_input)
        split_controls.addWidget(split_btn)
        split_controls.addStretch()
        split_layout.addLayout(split_controls)

        # Add PDF preview
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        pdf_label = QLabel()
        pdf_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll.setWidget(pdf_label)
        split_layout.addWidget(scroll)

        # Store references
        self.split_preview_label = pdf_label
        self.split_scroll = scroll

        # Add zoom functionality to scroll area
        scroll.wheelEvent = self.handle_split_zoom

        return split_page

    def split_pdf(self):
        """Split PDF into separate files based on page ranges"""
        if not self.current_pdf:
            QMessageBox.warning(self, "Warning", "Please open a PDF first")
            return

        try:
            # Get page ranges from input
            ranges_text = self.split_input.text().strip()
            if not ranges_text:
                QMessageBox.warning(self, "Warning", "Please enter page ranges")
                return

            # explain page ranges (format: "1,4;2-3;5-6")
            try:
                parts = ranges_text.split(";")
                page_groups = []

                for part in parts:
                    pages = set()
                    segments = part.split(",")

                    for segment in segments:
                        segment = segment.strip()
                        if "-" in segment:
                            # Handle range (e.g., "2-5")
                            start, end = map(int, segment.split("-"))
                            # Convert to 0-based index
                            pages.update(range(start - 1, end))
                        else:
                            # Handle single page
                            pages.add(int(segment) - 1)

                    # Convert to sorted list
                    page_groups.append(sorted(pages))

                # Validate page numbers
                all_pages = [p for group in page_groups for p in group]
                if any(p < 0 or p >= len(self.current_pdf) for p in all_pages):
                    raise ValueError("Invalid page numbers")

            except ValueError:
                QMessageBox.warning(self, "Warning", "Please enter valid page numbers in format: 1,4;2-3;5-6")
                return

            # Get output directory
            output_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory")
            if not output_dir:
                return

            # Create a subfolder for split files
            base_name = self.current_pdf.name.rsplit(".", 1)[0].split("/")[-1].split("\\")[-1]
            split_folder = f"{output_dir}/{base_name}_split"
            os.makedirs(split_folder, exist_ok=True)

            # Create PDFs for each group
            for i, pages in enumerate(page_groups):
                # Create new PDF document
                output_pdf = fitz.open()

                # Add pages from the group
                for page_num in pages:
                    output_pdf.insert_pdf(self.current_pdf, from_page=page_num, to_page=page_num)

                # Save the split PDF
                output_path = f"{split_folder}/part{i+1}.pdf"
                output_pdf.save(output_path)
                output_pdf.close()

            QMessageBox.information(self, "Success", f"PDF split successfully into {len(page_groups)} parts!")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error splitting PDF: {str(e)}")

    # == merge page ================================================================================================================================
    def create_merge_page(self):
        """Create the merge page with PDF merging functionality"""
        # Create merge page
        merge_page = QWidget()
        merge_layout = QVBoxLayout()
        merge_page.setLayout(merge_layout)

        # Add merge page buttons vertically
        add_btn = QPushButton("Add PDF")
        merge_btn = QPushButton("Merge PDFs")
        add_btn.clicked.connect(self.add_to_merge)
        merge_btn.clicked.connect(self.merge_pdfs)
        # Set size and font for buttons
        for btn in [add_btn, merge_btn]:
            btn.setMinimumHeight(40)
            font = btn.font()
            font.setPointSize(11)
            btn.setFont(font)
        merge_layout.addWidget(add_btn)
        merge_layout.addWidget(merge_btn)
        merge_layout.addSpacing(5)

        # Create table for merge list
        self.merge_table = QTableWidget()
        self.merge_table.setColumnCount(2)
        self.merge_table.setHorizontalHeaderLabels(["File Name", "Action"])
        self.merge_table.setMinimumHeight(300)
        self.merge_table.setColumnWidth(0, 450)
        merge_layout.addWidget(self.merge_table)

        return merge_page

    def add_to_merge(self):
        """Add one or more PDFs to the merge list (multi-select enabled)"""
        fnames, _ = QFileDialog.getOpenFileNames(self, "Open PDF(s)", "", "PDF files (*.pdf)")
        if fnames:
            added = False
            for fname in fnames:
                try:
                    # Verify it's a valid PDF
                    with open(fname, "rb") as file:
                        if file.read(4) != b"%PDF":
                            raise ValueError(f"{fname} is not a valid PDF file")
                    if fname not in self.merge_list:
                        self.merge_list.append(fname)
                        added = True
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Error adding PDF: {str(e)}")
            if added:
                self.update_merge_table()

    def update_merge_table(self):
        """Update the merge list table"""
        self.merge_table.setRowCount(len(self.merge_list))
        for i, pdf_path in enumerate(self.merge_list):
            try:
                # Add filename (use backslashes for Windows paths)
                filename = pdf_path.replace("/", "\\").split("\\")[-1]
                self.merge_table.setItem(i, 0, QTableWidgetItem(filename))

                # Add remove button
                remove_btn = QPushButton("Remove")
                remove_btn.clicked.connect(lambda checked, row=i: self.remove_from_merge(row))
                self.merge_table.setCellWidget(i, 1, remove_btn)
            except Exception as e:
                print(f"Error updating table row {i}: {str(e)}")

    def remove_from_merge(self, row):
        """Remove a PDF from the merge list"""
        self.merge_list.pop(row)
        self.update_merge_table()

    def merge_pdfs(self):
        """Merge selected PDFs into a single file"""
        if not self.merge_list:
            QMessageBox.warning(self, "Warning", "Please add PDF files to merge first!")
            return
        if len(self.merge_list) < 2:
            QMessageBox.warning(self, "Warning", "Please add at least 2 PDF files to merge!")
            return

        try:
            # Create output PDF
            output_pdf = fitz.open()

            # Add all PDFs to the output
            for pdf_path in self.merge_list:
                pdf = fitz.open(pdf_path)
                output_pdf.insert_pdf(pdf)
                pdf.close()

            # Save merged PDF
            fname, _ = QFileDialog.getSaveFileName(self, "Save Merged PDF", "", "PDF files (*.pdf)")
            if fname:
                output_pdf.save(fname)
                output_pdf.close()
                QMessageBox.information(self, "Success", "PDFs merged successfully!")

                # Clear the merge list and table
                self.merge_list = []
                self.update_merge_table()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error merging PDFs: {str(e)}")

    # == Page Navigation and Zoom ================================================================================================================================
    def prev_page(self):
        """Go to previous page"""
        if self.current_pdf and isinstance(self.current_page, int) and self.current_page > 0:
            # self.add_to_history(self.current_page)
            self.current_page -= 1
            self.display_page()

    def next_page(self):
        """Go to next page"""
        if self.current_pdf and isinstance(self.current_page, int) and self.current_page < len(self.current_pdf) - 1:
            # self.add_to_history(self.current_page)
            self.current_page += 1
            self.display_page()

    def handle_zoom(self, event):
        """Handle zoom with Ctrl+Mouse wheel for viewer page"""
        if event.modifiers() & Qt.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_factor *= 1.2  # Zoom in
            else:
                self.zoom_factor /= 1.2  # Zoom out
            self.zoom_factor = max(Config.ZOOM_LIMITS[0], min(self.zoom_factor, Config.ZOOM_LIMITS[1]))  # Limit zoom range
            # Update zoom labels
            self.zoom_label.setText(f"{int(self.zoom_factor * 100)}%")
            if hasattr(self, "split_zoom_label"):
                self.split_zoom_label.setText(f"{int(self.zoom_factor * 100)}%")
            self.display_page()  # Refresh display with new zoom
        else:
            # Normal scroll behavior
            QScrollArea.wheelEvent(self.scroll, event)

    def handle_split_zoom(self, event):
        """Handle zoom with Ctrl+Mouse wheel for split page"""
        if event.modifiers() & Qt.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_factor *= 1.2  # Zoom in
            else:
                self.zoom_factor /= 1.2  # Zoom out
            self.zoom_factor = max(Config.ZOOM_LIMITS[0], min(self.zoom_factor, Config.ZOOM_LIMITS[1]))  # Limit zoom range
            # Update zoom labels
            if hasattr(self, "split_zoom_label"):
                self.split_zoom_label.setText(f"{int(self.zoom_factor * 100)}%")
            self.zoom_label.setText(f"{int(self.zoom_factor * 100)}%")
            self.display_page()  # Refresh display with new zoom
        else:
            # Normal scroll behavior
            QScrollArea.wheelEvent(self.split_scroll, event)

    # == PDF Operations ============================================================================================================================================
    def open_pdf(self):
        """Load and display a PDF file"""
        try:
            fname = self._get_open_filename("Open PDF")
            if not fname:
                return

            if not self._validate_pdf_file(fname):
                return

            self._load_and_display_pdf(fname)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading PDF: {str(e)}")

    def _get_open_filename(self, title):
        """Get open filename with PDF filter"""
        fname, _ = QFileDialog.getOpenFileName(self, title, "", Config.PDF_FILTER)
        return fname

    def _validate_pdf_file(self, fname):
        """Validate that file is a PDF"""
        try:
            with open(fname, "rb") as file:
                if file.read(4) != Config.PDF_MAGIC_NUMBER:
                    QMessageBox.warning(self, "Warning", "Not a valid PDF file")
                    return False
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error validating PDF: {str(e)}")
            return False

    def _load_and_display_pdf(self, fname):
        """Load PDF file and update display"""
        self.close_pdf()

        try:
            self.current_pdf = fitz.open(fname)
            if not self.current_pdf.is_pdf:
                raise ValueError("Not a valid PDF file")

            # Reset view state for new PDF
            self.current_page = 0
            self.zoom_factor = 1.0

            # update page input and total pages
            self._update_page_controls()

            # Load thumbnails if we're in viewer mode
            if hasattr(self, 'thumbnail_widget'):
                self.thumbnail_widget.load_thumbnails(self.current_pdf)
                # Enforce thumbnail panel width
                self.viewer_splitter.setSizes([270, self.width() - 270])

            self.display_page()

        except Exception as e:
            self.close_pdf()
            raise

    def _update_page_controls(self):
        """Update all page number displays"""
        total_pages = len(self.current_pdf)
        self.total_pages_label.setText(f"/ {total_pages}")
        self.page_input.setText("1")

        if hasattr(self, "split_total_pages_label"):
            self.split_total_pages_label.setText(f"/ {total_pages}")
        if hasattr(self, "split_page_input"):
            self.split_page_input.setText("1")

    def close_pdf(self):
        """Close the current PDF document and clear all views"""
        try:
            # Clear all PDF display labels
            if hasattr(self, "pdf_label"):
                self.pdf_label.clear()
                self.pdf_label.update()
            if hasattr(self, "split_preview_label"):
                self.split_preview_label.clear()
                self.split_preview_label.update()

            # Clear thumbnails
            if hasattr(self, "thumbnail_widget"):
                self.thumbnail_widget.load_thumbnails(None)

            # Reset zoom factor
            self.zoom_factor = 1.0
            if hasattr(self, "zoom_label"):
                self.zoom_label.setText("100%")
            if hasattr(self, "split_zoom_label"):
                self.split_zoom_label.setText("100%")

            # Reset page displays
            # Viewer page
            self.page_input.setText("")
            self.total_pages_label.setText("/ 0")

            # Split page
            if hasattr(self, "split_page_input"):
                self.split_page_input.setText("")
            if hasattr(self, "split_total_pages_label"):
                self.split_total_pages_label.setText("/ 0")
            if hasattr(self, "split_input"):
                self.split_input.clear()

            # Close PDF document
            if self.current_pdf:
                self.current_pdf.close()
                self.current_pdf = None
                self.current_page = None

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error closing PDF: {str(e)}")

    # == Reuseable Methods ============================================================================================================================================

    def go_to_page(self):
        """Go to specific page number"""
        try:
            if not self.current_pdf:
                return

            # Get page number from input, convert to 0-based index
            page_num = int(self.page_input.text()) - 1

            # Validate page number
            if 0 <= page_num < len(self.current_pdf):
                # self.add_to_history(self.current_page)  # Add current page to history
                self.current_page = page_num
                self.display_page()
            else:
                # Reset to current page
                self.page_input.setText(str(self.current_page + 1))
                QMessageBox.warning(self, "Warning", "Invalid page number")
        except ValueError:
            # Reset to current page if input is not a number
            self.page_input.setText(str(self.current_page + 1))
            QMessageBox.warning(self, "Warning", "Please enter a valid page number")

    def display_page(self):
        """Display the current PDF page with zoom factor"""
        if not self.current_pdf or not isinstance(self.current_page, int):
            return

        try:
            # Get the current page from the PDF
            page = self.current_pdf[self.current_page]

            # Update page input in both viewer and split pages
            self.page_input.setText(str(self.current_page + 1))
            if hasattr(self, "split_page_input"):
                self.split_page_input.setText(str(self.current_page + 1))

            # Use matrix for better quality rendering
            matrix = fitz.Matrix(self.zoom_factor, self.zoom_factor)
            pix = page.get_pixmap(matrix=matrix, alpha=False)

            # Convert to QImage and QPixmap efficiently
            img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(img)

            # Update the display in both viewer and split pages
            self.pdf_label.setPixmap(pixmap)
            if hasattr(self, "split_preview_label"):
                self.split_preview_label.setPixmap(pixmap)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error displaying PDF: {str(e)}")

    def zoom_view(self, factor):
        """Zoom the viewer page"""
        self._apply_zoom_factor(factor)
        self._update_zoom_displays()
        self.display_page()

    def update_zoom_from_input(self, text):
        """Update zoom based on input percentage"""
        try:
            zoom = self._parse_zoom_input(text)
            if zoom is not None:
                self.zoom_factor = zoom
                self._update_zoom_displays()
                if self.current_pdf:
                    self.display_page()
        except ValueError:
            self._update_zoom_displays()

    def _apply_zoom_factor(self, factor):
        """Apply zoom factor with limits"""
        self.zoom_factor *= factor
        self.zoom_factor = max(Config.ZOOM_LIMITS[0], min(self.zoom_factor, Config.ZOOM_LIMITS[1]))

    def _parse_zoom_input(self, text):
        """Parse and validate zoom input"""
        try:
            zoom = float(text.strip("%")) / 100.0
            return max(Config.ZOOM_LIMITS[0], min(zoom, Config.ZOOM_LIMITS[1]))
        except ValueError:
            return None

    def _update_zoom_displays(self):
        """Update all zoom displays"""
        zoom_text = f"{int(self.zoom_factor * 100)}%"
        self.zoom_label.setText(zoom_text)
        if hasattr(self, "split_zoom_label"):
            self.split_zoom_label.setText(zoom_text)

    def keyPressEvent(self, event):
        """Handle keyboard events for navigation"""
        if event.key() == Qt.Key_Left:
            self.prev_page()
        elif event.key() == Qt.Key_Right:
            self.next_page()
        event.accept()



def main():
    """Application entry point with error handling"""
    try:
        app = QApplication(sys.argv)
        try:
            app.setWindowIcon(QIcon("icon.ico"))
        except Exception as e:
            print(f"Warning: Could not load application icon: {e}")

        window = PDFApp()
        window.show()
        return app.exec_()
    except Exception as e:
        print(f"Error starting application: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
