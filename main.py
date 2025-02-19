import sys
import os
import json
import logging
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QListWidget, QLabel, 
                           QSlider, QFileDialog, QComboBox, QDialog, QMenu, QFormLayout, 
                           QLineEdit, QDialogButtonBox, QMessageBox)
from PyQt6.QtCore import Qt, QUrl, QTimer, QByteArray
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtGui import QPixmap, QImage
from mutagen import File
from mutagen.id3 import APIC
from mutagen.id3 import ID3, TIT2, TPE1, APIC
import random

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    force=True
)
class AudioPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Local Audio Player")
        self.setMinimumSize(800, 600)
        
        # Media player setup
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        
        # Track management
        self.current_playlist = []
        self.current_index = -1
        self.genres = {}  # Dictionary to store genre: [tracks]
        self.scanned_folders = set()  # Keep track of scanned folders
        
        # Load saved data
        self.config_file = os.path.join(os.path.expanduser("~"), ".audio_player_config.json")
        self.load_saved_data()
        
        # Create UI elements
        self.create_ui_elements()
        self.init_ui()
        self.setup_connections()
        
        # Update the playlist if we have any saved tracks
        self.update_playlist()

    def refresh_library(self):
        """Refresh all tracks in the library by rescanning folders and updating metadata"""
        # Store current folders
        folders_to_rescan = self.scanned_folders.copy()
        
        # Clear current library
        self.genres.clear()
        self.scanned_folders.clear()
        self.genre_combo.clear()
        self.genre_combo.addItem("All Genres")
        
        # Rescan all folders
        for folder in folders_to_rescan:
            if os.path.exists(folder):
                self.scan_folder(folder)
        
        # Update the playlist view
        self.update_playlist()
        
        # Save the refreshed data
        self.save_data()

    def scan_folder(self, folder_path):
        """Scan folder for audio files with duplicate prevention"""
        logging.info(f"Scanning folder: {folder_path}")
                
        supported_formats = ['.mp3', '.wav', '.flac', '.m4a', '.ogg']
        
        for root, _, files in os.walk(folder_path):
            genre = os.path.basename(root)
            logging.info(f"Processing directory: {root} (genre: {genre})")
            
            if genre not in self.genres:
                self.genres[genre] = []
                self.genre_combo.addItem(genre)
            
            # Clear existing tracks for this genre
            self.genres[genre] = []
            
            for file in files:
                if any(file.lower().endswith(fmt) for fmt in supported_formats):
                    file_path = os.path.join(root, file)
                    logging.info(f"Found audio file: {file_path}")
                    
                    # Extract metadata from the file
                    logging.info(f"Extracting metadata for: {file_path}")
                    metadata = self.extract_metadata(file_path)
                    logging.info(f"Extracted metadata: {metadata}")
                    
                    self.genres[genre].append({
                        'path': file_path,
                        'title': metadata['title'],
                        'artist': metadata['artist'],
                        'album_art': metadata['album_art']
                    })
        
        self.scanned_folders.add(folder_path)
        self.update_playlist()
        self.save_data()

    def create_ui_elements(self):
        """Create all UI elements and store them as class attributes"""
        # Create control buttons first
        self.prev_button = QPushButton("⏮")
        self.play_button = QPushButton("▶")
        self.next_button = QPushButton("⏭")
        self.volume_button = QPushButton("🕨")
        self.refresh_button = QPushButton("↺")
        self.remove_button = QPushButton("🗑")
        
        # Set button tooltips
        self.volume_button.setToolTip("Volume")
        self.refresh_button.setToolTip("Refresh Library")
        self.remove_button.setToolTip("Remove Selected")
        
        # Set object names for specific styling
        self.play_button.setObjectName("playButton")
        self.volume_button.setObjectName("volumeButton")
        
        # Create progress slider
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        
        # Create track information labels
        self.track_title = QLabel("No Track Playing")
        self.track_artist = QLabel("Unknown Artist")
        
        # Create time labels
        self.time_current = QLabel("0:00")
        self.time_total = QLabel("0:00")
        
        # Create playlist and genre elements
        self.playlist_widget = QListWidget()
        self.genre_combo = QComboBox()
        self.genre_combo.addItem("All Genres")
        for genre in self.genres.keys():
            self.genre_combo.addItem(genre)
        
        # Create album art label
        self.album_art = QLabel()
        self.album_art.setFixedSize(300, 300)

        # Create volume slider and popup
        self._setup_volume_controls()
        
        # Apply styles
        self._apply_styles()
        self.clear_button = QPushButton("🗑️")
        self.clear_button.setToolTip("Clear Library")
        self.clear_button.clicked.connect(self.clear_library)

    def _setup_volume_controls(self):
        """Setup volume slider and popup"""
        # Create volume slider
        self.volume_slider = QSlider(Qt.Orientation.Vertical)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setFixedHeight(100)
        self.volume_slider.setFixedWidth(20)  # Make the slider wider
        self.volume_slider.setInvertedControls(True)  # Make sliding up increase volume
        self.volume_slider.setStyleSheet("""
            QSlider::groove:vertical {
                background: #2d2e32;
                width: 8px;
                border-radius: 4px;
            }
            QSlider::handle:vertical {
                background: white;
                height: 18px;
                width: 18px;
                margin: -4px -5px;
                border-radius: 9px;
                border: 1px solid #2d2e32;
            }
            QSlider::add-page:vertical {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                        stop:0 #4CAF50,
                                        stop:0.5 #2196F3,
                                        stop:1 #9C27B0);
                width: 8px;
                border-radius: 4px;
            }
        """)
        
        # Create volume level label
        self.volume_label = QLabel("50%")
        self.volume_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 12px;
                padding: 2px;
                background: transparent;
                min-width: 40px;
                text-align: center;
            }
        """)
        
        # Create volume popup
        self.volume_popup = QWidget(self)
        self.volume_popup.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.volume_popup.setStyleSheet("""
            QWidget {
                background-color: #2d2e32;
                border: 1px solid #3d3e42;
                border-radius: 10px;
            }
        """)
        
        # Setup volume popup layout with label
        volume_popup_layout = QVBoxLayout(self.volume_popup)
        volume_popup_layout.setContentsMargins(10, 10, 10, 10)
        volume_popup_layout.setSpacing(5)
        volume_popup_layout.addWidget(self.volume_label, alignment=Qt.AlignmentFlag.AlignCenter)
        volume_popup_layout.addWidget(self.volume_slider, alignment=Qt.AlignmentFlag.AlignCenter)
        self.volume_popup.setFixedSize(50, 160)
        self.volume_popup.hide()
        
    def _apply_styles(self):
        """Apply styles to all UI elements"""
        # Main window and general styles
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                        stop:0 #1a1b1e,
                                        stop:1 #2d2e32);
                color: white;
            }
            QLabel {
                color: white;
            }
            QPushButton {
                background-color: #2d2e32;
                color: white;
                border: none;
                border-radius: 20px;
                padding: 8px;
                font-size: 16px;
                min-width: 40px;
                min-height: 40px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #3d3e42;
            }
            QPushButton#playButton {
                min-width: 50px;
                min-height: 50px;
                border-radius: 25px;
                font-size: 20px;
            }
            QListWidget {
                background-color: rgba(45, 46, 50, 0.7);
                color: white;
                border: none;
                border-radius: 20px;
                padding: 10px;
            }
            QListWidget::item {
                border-radius: 10px;
                padding: 8px;
                margin: 2px;
            }
            QListWidget::item:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
            QListWidget::item:selected {
                background-color: rgba(255, 255, 255, 0.2);
            }
            QComboBox {
                background-color: rgba(45, 46, 50, 0.7);
                color: white;
                border: none;
                border-radius: 15px;
                padding: 8px;
                margin: 5px;
            }
            QSlider {
                height: 20px;
            }
        """)
        
        # Volume popup style
        self.volume_popup.setStyleSheet("""
            QWidget {
                background-color: rgba(45, 46, 50, 0.95);
                border-radius: 15px;
                padding: 10px;
            }
        """)
        
        # Track information styles
        self.track_title.setStyleSheet("font-size: 24px; font-weight: bold;")
        self.track_artist.setStyleSheet("font-size: 16px; color: #aaaaaa;")
        
        # Album art style
        self.album_art.setStyleSheet("""
            QLabel {
                background-color: rgba(45, 46, 50, 0.7);
                border-radius: 20px;
                min-width: 300px;
                min-height: 300px;
            }
        """)
        
        # Set default album art
        self.set_default_album_art()

    def init_ui(self):
        """Initialize the UI layout"""
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(30)
        
        # Create and setup left panel (Playlist and Genre)
        left_panel = self._create_left_panel()
        
        # Create and setup right panel (Player controls)
        right_panel = self._create_right_panel()
        
        # Add panels to main layout with proper minimum widths
        left_panel.setMinimumWidth(300)  # Set minimum width for left panel
        right_panel.setMinimumWidth(400)  # Set minimum width for right panel
        
        # Add panels to main layout with proper proportions
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel, 2) 

    def create_context_menu(self, position):
        menu = QMenu(self)  # Add parent
        selected_items = self.playlist_widget.selectedItems()
        
        if selected_items:
            edit_metadata = menu.addAction("Edit Metadata")
            edit_metadata.triggered.connect(self.show_metadata_editor)
            
            # Change menu.exec to specify position
            menu.exec(self.playlist_widget.mapToGlobal(position))

    def show_metadata_editor(self):
        
        # Get selected track
        selected_items = self.playlist_widget.selectedItems()
        if not selected_items:
            return
            
        track_index = self.playlist_widget.row(selected_items[0])
        track = self.current_playlist[track_index]
        
        # Create dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Track Metadata")
        layout = QFormLayout()
        
        # Create input fields
        title_input = QLineEdit(track.get('title', ''))
        artist_input = QLineEdit(track.get('artist', ''))
        image_path = QLineEdit()
        
        # Add browse button for image
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(lambda: image_path.setText(
            QFileDialog.getOpenFileName(dialog, "Select Album Art", "", "Images (*.png *.jpg)")[0]
        ))
        
        image_layout = QHBoxLayout()
        image_layout.addWidget(image_path)
        image_layout.addWidget(browse_button)
        
        # Add fields to layout
        layout.addRow("Title:", title_input)
        layout.addRow("Artist:", artist_input)
        layout.addRow("Album Art:", image_layout)
        
        # Add buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        
        dialog.setLayout(layout)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Update metadata using mutagen
            try:
                # Load or create ID3 tags
                try:
                    audio = ID3(track['path'])
                except:
                    audio = ID3()
                    
                # Update title
                if title_input.text():
                    audio['TIT2'] = TIT2(encoding=3, text=title_input.text())
                
                # Update artist
                if artist_input.text():
                    audio['TPE1'] = TPE1(encoding=3, text=artist_input.text())
                
                # Update album art
                if image_path.text():
                    with open(image_path.text(), 'rb') as img:
                        img_data = img.read()
                        audio['APIC:'] = APIC(
                            encoding=3,
                            mime='image/jpeg',
                            type=3,
                            desc='Cover',
                            data=img_data
                        )
                
                # Save changes to file
                audio.save(track['path'])
                
                # Refresh the track in the library
                self.refresh_library()
                
                QMessageBox.information(self, "Success", "Metadata updated successfully!")
                
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to update metadata: {str(e)}")

    def _create_left_panel(self):
        """Create and return the left panel with playlist controls"""
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(20, 20, 20, 20)
        
        # Add buttons at the top
        top_buttons_layout = QHBoxLayout()
        
        # Create and style add folder button
        add_folder_btn = QPushButton("+")
        add_folder_btn.clicked.connect(self.add_folder)
        
        # Add all buttons to the top layout
        top_buttons_layout.addWidget(add_folder_btn)
        top_buttons_layout.addWidget(self.refresh_button)
        top_buttons_layout.addWidget(self.clear_button)
        
        left_layout.addLayout(top_buttons_layout)
        
        # Add genre selector
        left_layout.addWidget(self.genre_combo)
        
        # Add playlist with a label
        playlist_label = QLabel("Playlist")
        playlist_label.setStyleSheet("font-size: 22px; font-weight: bold; margin-top: 10px;")
        left_layout.addWidget(playlist_label)
        left_layout.addWidget(self.playlist_widget)
        
        return left_panel

    def _create_right_panel(self):
        """Create and return the right panel with player controls"""
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(20, 20, 20, 20)
        right_layout.setSpacing(30)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Create a container widget for the content to allow centering
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(30)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        
        # Add album art and track info
        album_container = self._create_album_container()
        content_layout.addWidget(album_container, alignment=Qt.AlignmentFlag.AlignHCenter)
        
        # Add progress controls
        slider_container = self._create_slider_container()
        content_layout.addWidget(slider_container)
        
        # Add playback controls
        controls_container = self._create_controls_container()
        content_layout.addWidget(controls_container)
        
        # Add the content widget to the right panel with stretch
        right_layout.addStretch(1)
        right_layout.addWidget(content_widget)
        right_layout.addStretch(1)
        
        return right_panel

    def _create_album_container(self):
        """Create container for album art and track info"""
        album_container = QWidget()
        album_layout = QVBoxLayout(album_container)
        album_layout.setContentsMargins(0, 0, 0, 0)
        album_layout.setSpacing(20)
        album_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        
        # Add album art
        album_layout.addWidget(self.album_art, alignment=Qt.AlignmentFlag.AlignHCenter)
        
        # Add track information
        track_info_container = QWidget()
        track_info_layout = QVBoxLayout(track_info_container)
        track_info_layout.setContentsMargins(0, 0, 0, 0)
        track_info_layout.setSpacing(5)
        track_info_layout.addWidget(self.track_title, alignment=Qt.AlignmentFlag.AlignHCenter)
        track_info_layout.addWidget(self.track_artist, alignment=Qt.AlignmentFlag.AlignHCenter)
        album_layout.addWidget(track_info_container)
        
        return album_container

    def _create_slider_container(self):
        """Create container for progress slider and time labels"""
        slider_container = QWidget()
        slider_container.setMinimumWidth(400)  # Minimum width
        slider_container.setMaximumWidth(600)  # Maximum width
        slider_layout = QVBoxLayout(slider_container)
        slider_layout.setSpacing(5)
        slider_layout.setContentsMargins(10, 0, 10, 0)  # Increased margins to account for slider handle
        
        # Setup progress slider
        self.progress_slider.setFixedHeight(20)
        self.progress_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: #2d2e32;
                height: 4px;
                border-radius: 2px;
                margin: 0 9px;  /* Half the handle width to prevent overflow */
            }
            QSlider::handle:horizontal {
                background: white;
                width: 18px;
                height: 18px;
                margin: -7px -9px;  /* Negative margin to compensate for handle width */
                border-radius: 9px;
            }
            QSlider::add-page:horizontal {
                background: #2d2e32;
            }
            QSlider::sub-page:horizontal {
                background: #4CAF50;
                border-radius: 2px;
            }
        """)
        slider_layout.addWidget(self.progress_slider)
        
        # Time labels layout with proper alignment
        time_layout = QHBoxLayout()
        time_layout.setContentsMargins(0, 0, 0, 0)
        
        # Style time labels
        self.time_current.setStyleSheet("""
            QLabel {
                min-width: 50px;  /* Ensure enough space for "60:00" */
                color: #aaaaaa;
            }
        """)
        self.time_total.setStyleSheet("""
            QLabel {
                min-width: 50px;  /* Ensure enough space for "60:00" */
                color: #aaaaaa;
            }
        """)
        
        time_layout.addWidget(self.time_current)
        time_layout.addStretch()
        time_layout.addWidget(self.time_total)
        slider_layout.addLayout(time_layout)
        
        return slider_container

    def _create_controls_container(self):
        """Create container for playback control buttons"""
        controls_container = QWidget()
        controls_container.setMinimumWidth(400)  # Minimum width
        controls_container.setMaximumWidth(600)  # Maximum width
        controls_layout = QHBoxLayout(controls_container)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(30)
        controls_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        
        # Create inner container for buttons to ensure centered alignment
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(30)
        
        # Add buttons to the inner container
        button_layout.addWidget(self.prev_button)
        button_layout.addWidget(self.play_button)
        button_layout.addWidget(self.next_button)
        button_layout.addWidget(self.volume_button)
        
        # Center the button container in the main container
        controls_layout.addStretch()
        controls_layout.addWidget(button_container)
        controls_layout.addStretch()
        
        return controls_container

    def remove_selected(self):
        """Remove selected tracks or entire genre"""
        current_genre = self.genre_combo.currentText()
        selected_items = self.playlist_widget.selectedItems()
        
        if not selected_items:
            return
            
        if current_genre == "All Genres":
            # Remove selected tracks from their respective genres
            for item in selected_items:
                track_index = self.playlist_widget.row(item)
                track = self.current_playlist[track_index]
                genre = track['genre']
                
                # Remove track from its genre
                self.genres[genre] = [t for t in self.genres[genre] 
                                    if t['path'] != track['path']]
                
                # Remove genre if empty
                if not self.genres[genre]:
                    del self.genres[genre]
                    self.genre_combo.removeItem(self.genre_combo.findText(genre))
        else:
            # Remove selected tracks from current genre
            selected_indices = {self.playlist_widget.row(item) for item in selected_items}
            self.genres[current_genre] = [track for i, track in enumerate(self.genres[current_genre])
                                        if i not in selected_indices]
            
            # Remove genre if empty
            if not self.genres[current_genre]:
                del self.genres[current_genre]
                self.genre_combo.removeItem(self.genre_combo.findText(current_genre))
                self.genre_combo.setCurrentText("All Genres")
        
        # Update playlist and save changes
        self.update_playlist()
        self.save_data()

    def load_saved_data(self):
        """Load saved genres and folders from config file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    self.genres = data.get('genres', {})
                    self.scanned_folders = set(data.get('folders', []))
                    
                    # Validate and update existing tracks with new fields
                    for genre in list(self.genres.keys()):
                        updated_tracks = []
                        for track in self.genres[genre]:
                            if os.path.exists(track['path']):
                                # Add missing fields for older tracks
                                if 'artist' not in track:
                                    metadata = self.extract_metadata(track['path'])
                                    track['artist'] = metadata['artist']
                                    track['title'] = metadata['title']
                                updated_tracks.append(track)
                        self.genres[genre] = updated_tracks
                    
                    # Save the updated data
                    self.save_data()
        except Exception as e:
            print(f"Error loading saved data: {e}")
            self.genres = {}
            self.scanned_folders = set()

    def save_data(self):
        """Save current genres and folders to config file"""
        try:
            data = {
                'genres': self.genres,
                'folders': list(self.scanned_folders)
            }
            with open(self.config_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Error saving data: {e}")

    def closeEvent(self, event):
        """Override close event to save data before closing"""
        self.save_data()
        super().closeEvent(event)

    def update_playlist(self):
        """Update the playlist view based on current genre selection"""
        self.playlist_widget.clear()
        current_genre = self.genre_combo.currentText()
        
        if current_genre == "All Genres":
            self.current_playlist = []
            for genre, tracks in self.genres.items():
                for track in tracks:
                    # Ensure each track has a genre field
                    track_copy = track.copy()
                    track_copy['genre'] = genre
                    self.current_playlist.append(track_copy)
        else:
            self.current_playlist = [
                {**track, 'genre': current_genre} 
                for track in self.genres.get(current_genre, [])
            ]
        
        for track in self.current_playlist:
            self.playlist_widget.addItem(track['title'])

    def set_default_album_art(self):
        """Set a default music note icon as album art"""
        # Create a default album art with a music note
        default_art = QPixmap(300, 300)
        default_art.fill(Qt.GlobalColor.transparent)
        self.album_art.setPixmap(default_art)
        self.album_art.setStyleSheet("""
            QLabel {
                background-color: #2d2e32;
                border-radius: 20px;
                min-width: 300px;
                min-height: 300px;
                qproperty-alignment: AlignCenter;
                font-size: 48px;
            }
        """)
        self.album_art.setText("🎵")  # Music note emoji as default

    def update_album_art(self, album_art_data):
        """Update the album art display with new image data"""
        if album_art_data:
            try:
                logging.info(f"Attempting to display album art, data size: {len(album_art_data)} bytes")
                
                # Convert the bytes to QByteArray
                byte_array = QByteArray(album_art_data)
                
                # Create QImage from the data
                qimg = QImage.fromData(byte_array)
                if qimg.isNull():
                    logging.error("Failed to create QImage from album art data")
                    self.set_default_album_art()
                    return
                
                logging.info(f"Created QImage: {qimg.width()}x{qimg.height()}")
                
                # Create and scale pixmap
                pixmap = QPixmap.fromImage(qimg)
                scaled_pixmap = pixmap.scaled(
                    300, 300,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                
                # Set the pixmap and style
                self.album_art.setPixmap(scaled_pixmap)
                self.album_art.setText("")  # Clear any text (e.g., the music note)
                self.album_art.setStyleSheet("""
                    QLabel {
                        background-color: #2d2e32;
                        border-radius: 20px;
                        min-width: 300px;
                        min-height: 300px;
                        padding: 10px;
                    }
                """)
                logging.info("Successfully set album art")
            except Exception as e:
                logging.error(f"Error setting album art: {e}", exc_info=True)
                self.set_default_album_art()
        else:
            logging.info("No album art data provided, setting default")
            self.set_default_album_art()

    def add_folder(self):
        """Open file dialog to select and add a music folder"""
        folder = QFileDialog.getExistingDirectory(self, "Select Music Folder")
        if folder:
            self.scan_folder(folder)

    def extract_metadata(self, file_path):
        """Extract metadata from audio file including artist and album art"""
        try:
            logging.info(f"\n{'='*50}\nExtracting metadata from: {file_path}")
            audio = File(file_path)
            
            # Default metadata
            metadata = {
                'title': os.path.splitext(os.path.basename(file_path))[0],
                'artist': 'Unknown Artist',
                'album_art': None
            }
            
            if audio is not None:
                logging.info(f"Audio file type: {type(audio).__name__}")
                
                if hasattr(audio, 'tags') and audio.tags:
                    # Get all available tags for debugging
                    all_tags = list(audio.tags.keys())
                    logging.info(f"All available tags: {all_tags}")
                    
                    # Look for APIC tags
                    apic_candidates = [tag for tag in all_tags if 'APIC' in str(tag)]
                    logging.info(f"Found APIC candidates: {apic_candidates}")
                    
                    # Try to get album art
                    if apic_candidates:
                        for key in apic_candidates:
                            try:
                                apic_tag = audio.tags[key]
                                logging.info(f"Attempting to read APIC tag: {key}")
                                logging.info(f"APIC tag type: {type(apic_tag)}")
                                
                                # Try to access the image data
                                if hasattr(apic_tag, 'data'):
                                    metadata['album_art'] = apic_tag.data
                                    logging.info(f"Successfully extracted album art data: {len(metadata['album_art'])} bytes")
                                    # Log the first few bytes for debugging
                                    logging.info(f"First 20 bytes of image data: {metadata['album_art'][:20]}")
                                    break
                                else:
                                    logging.warning(f"APIC tag {key} has no 'data' attribute")
                            except Exception as e:
                                logging.error(f"Error reading APIC tag {key}: {e}")
                    else:
                        logging.warning("No APIC tags found")
                    
                    # Get other metadata
                    if 'TIT2' in audio:
                        metadata['title'] = str(audio['TIT2'])
                    if 'TPE1' in audio:
                        metadata['artist'] = str(audio['TPE1'])
                    if 'TCON' in audio:
                        logging.info(f"Genre: {str(audio['TCON'])}")
                
                logging.info(f"Final metadata state:")
                logging.info(f"  Title: {metadata['title']}")
                logging.info(f"  Artist: {metadata['artist']}")
                logging.info(f"  Has Album Art: {metadata['album_art'] is not None}")
                
            return metadata
        except Exception as e:
            logging.error(f"Error extracting metadata: {str(e)}", exc_info=True)
            return {
                'title': os.path.splitext(os.path.basename(file_path))[0],
                'artist': 'Unknown Artist',
                'album_art': None
            }

    def toggle_playback(self):
        """Toggle between play and pause states"""
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            self.play_button.setText("▶")
        else:
            self.player.play()
            self.play_button.setText("⏸")

    def set_default_album_art(self):
        """Set a default music note icon as album art"""
        self.album_art.setText("🎵")
        self.album_art.setStyleSheet("""
            QLabel {
                background-color: #2d2e32;
                border-radius: 20px;
                min-width: 300px;
                min-height: 300px;
                qproperty-alignment: AlignCenter;
                font-size: 48px;
            }
        """)

    def update_album_art(self, album_art_data):
        """Update the album art display with new image data"""
        if album_art_data:
            try:
                logging.info(f"Attempting to display album art, data size: {len(album_art_data)} bytes")
                logging.info(f"First 20 bytes of image data: {album_art_data[:20]}")
                
                # Convert the bytes to QByteArray
                byte_array = QByteArray(album_art_data)
                logging.info(f"Created QByteArray, size: {byte_array.size()}")
                
                # Create QImage from the data
                qimg = QImage.fromData(byte_array)
                if qimg.isNull():
                    logging.error("Failed to create QImage from album art data")
                    self.set_default_album_art()
                    return
                
                logging.info(f"Successfully created QImage: {qimg.width()}x{qimg.height()}")
                
                # Create and scale pixmap
                pixmap = QPixmap.fromImage(qimg)
                scaled_pixmap = pixmap.scaled(
                    300, 300,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                
                # Clear any existing content
                self.album_art.clear()
                
                # Set the pixmap and style
                self.album_art.setPixmap(scaled_pixmap)
                self.album_art.setText("")  # Clear any text (e.g., the music note)
                self.album_art.setStyleSheet("""
                    QLabel {
                        background-color: #2d2e32;
                        border-radius: 20px;
                        min-width: 300px;
                        min-height: 300px;
                        padding: 10px;
                    }
                """)
                logging.info("Successfully set album art")
            except Exception as e:
                logging.error(f"Error setting album art: {e}", exc_info=True)
                self.set_default_album_art()
        else:
            logging.info("No album art data provided, setting default")
            self.set_default_album_art()

    def play_track(self, index):
        """Play the track at the given index"""
        if 0 <= index < len(self.current_playlist):
            self.current_index = index
            track = self.current_playlist[index]
            logging.info(f"Playing track: {track['path']}")
            logging.info(f"Track metadata: {track}")
            
            # Set the source and play
            self.player.setSource(QUrl.fromLocalFile(track['path']))
            self.player.play()
            self.play_button.setText("⏸")
            
            # Update track information with fallbacks
            title = track.get('title', os.path.splitext(os.path.basename(track['path']))[0])
            artist = track.get('artist', 'Unknown Artist')
            logging.info(f"Setting title: {title}, artist: {artist}")
            
            self.track_title.setText(title)
            self.track_artist.setText(artist)
            
            # Update album art
            if 'album_art' in track and track['album_art']:
                logging.info("Found album art in track metadata, attempting to display")
                self.update_album_art(track['album_art'])
            else:
                logging.info("No album art found in track metadata, using default")
                self.set_default_album_art()

    def play_next(self):
        if self.current_playlist:
            next_index = (self.current_index + 1) % len(self.current_playlist)
            self.play_track(next_index)

    def play_previous(self):
        if self.current_playlist:
            prev_index = (self.current_index - 1) % len(self.current_playlist)
            self.play_track(prev_index)

    def shuffle_playlist(self):
        """Shuffle the current playlist"""
        if self.current_playlist:
            current_track = None
            if 0 <= self.current_index < len(self.current_playlist):
                current_track = self.current_playlist[self.current_index]
                
            random.shuffle(self.current_playlist)
            
            # Update the playlist view
            self.playlist_widget.clear()
            for track in self.current_playlist:
                self.playlist_widget.addItem(track['title'])
                
            # Update current index if we had a track playing
            if current_track:
                self.current_index = self.current_playlist.index(current_track)

    def setup_connections(self):
        """Set up all signal connections"""
        # Connect playback buttons
        self.play_button.clicked.connect(self.toggle_playback)
        self.next_button.clicked.connect(self.play_next)
        self.prev_button.clicked.connect(self.play_previous)
        
        # Connect management buttons
        self.refresh_button.clicked.connect(self.refresh_library)
        self.remove_button.clicked.connect(self.remove_selected)
        
        # Connect sliders
        self.progress_slider.sliderMoved.connect(self.seek)
        self.volume_slider.valueChanged.connect(self.change_volume)
        
        # Connect playlist and genre controls
        self.playlist_widget.itemDoubleClicked.connect(self.playlist_double_clicked)
        self.genre_combo.currentTextChanged.connect(self.genre_changed)
        self.playlist_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.playlist_widget.customContextMenuRequested.connect(self.create_context_menu)
        
        # Connect media player signals
        self.player.positionChanged.connect(self.position_changed)
        self.player.durationChanged.connect(self.duration_changed)
        
        # Connect volume controls
        self.volume_button.clicked.connect(self.show_volume_popup)
        
        # Set initial volume
        initial_volume = 50  # 50% volume
        self.audio_output.setVolume(initial_volume / 100.0)
        self.volume_slider.setValue(initial_volume)
        self.change_volume(initial_volume)
        
    def show_volume_popup(self):
        """Show the volume slider popup near the volume button"""
        if self.volume_popup.isVisible():
            self.volume_popup.hide()
            self.removeEventFilter(self)
            return
            
        # Get the global position of the volume button
        button_pos = self.volume_button.mapToGlobal(self.volume_button.rect().center())
        
        # Position the popup above the button
        popup_x = button_pos.x() - self.volume_popup.width() // 2
        popup_y = button_pos.y() - self.volume_popup.height() - 5
        
        # Set the current volume value
        current_volume = int(self.audio_output.volume() * 100)
        self.volume_slider.setValue(current_volume)
        
        # Show the popup
        self.volume_popup.move(popup_x, popup_y)
        self.volume_popup.show()
        
        # Install event filter
        self.installEventFilter(self)
        
    def start_volume_popup_monitor(self):
        """Start monitoring for clicks outside the volume popup"""
        self.installEventFilter(self)
        
    def eventFilter(self, obj, event):
        """Filter events for the volume popup"""
        if event.type() == event.Type.MouseButtonPress:
            if not self.volume_popup.geometry().contains(event.globalPosition().toPoint()):
                self.volume_popup.hide()
                self.removeEventFilter(self)
        return super().eventFilter(obj, event)
        
    def change_volume(self, value):
        """Change the volume and update the icon and label"""
        volume = value / 100.0
        self.audio_output.setVolume(volume)
        
        # Update volume percentage label
        self.volume_label.setText(f"{value}%")
        
        # Update volume icon based on level
        if value == 0:
            self.volume_button.setText("🔇")
        elif value < 33:
            self.volume_button.setText("🔈")
        elif value < 66:
            self.volume_button.setText("🔉")
        else:
            self.volume_button.setText("🔊")

    def seek(self, position):
        self.player.setPosition(position)

    def format_time(self, milliseconds):
        """Convert milliseconds to mm:ss format"""
        seconds = int(milliseconds / 1000)
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes}:{seconds:02d}"
    
    def clear_library(self):
        """Clear all saved data and rescan library"""
        self.genres.clear()
        self.scanned_folders.clear()
        self.genre_combo.clear()
        self.genre_combo.addItem("All Genres")
        self.save_data()  # Save empty state

    def position_changed(self, position):
        """Handle position changes in the currently playing track"""
        self.progress_slider.setValue(position)
        self.time_current.setText(self.format_time(position))

    def duration_changed(self, duration):
        """Handle duration changes when loading a new track"""
        self.progress_slider.setRange(0, duration)
        self.time_total.setText(self.format_time(duration))

    def playlist_double_clicked(self, item):
        index = self.playlist_widget.row(item)
        self.play_track(index)

    def genre_changed(self, genre):
        self.update_playlist()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    player = AudioPlayer()
    player.show()
    sys.exit(app.exec())