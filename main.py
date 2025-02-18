import sys
import os
import json
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QListWidget, QLabel, 
                           QSlider, QFileDialog, QComboBox)
from PyQt6.QtCore import Qt, QUrl, QTimer, QByteArray
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtGui import QPixmap, QImage
from mutagen import File
import random

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
        if folder_path in self.scanned_folders:
            return
            
        supported_formats = ['.mp3', '.wav', '.flac', '.m4a', '.ogg']
        
        for root, _, files in os.walk(folder_path):
            genre = os.path.basename(root)
            
            if genre not in self.genres:
                self.genres[genre] = []
                self.genre_combo.addItem(genre)
            
            existing_paths = {track['path'] for track in self.genres[genre]}
            
            for file in files:
                if any(file.lower().endswith(fmt) for fmt in supported_formats):
                    file_path = os.path.join(root, file)
                    
                    if file_path in existing_paths:
                        continue
                    
                    # Extract metadata from the file
                    metadata = self.extract_metadata(file_path)
                    
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
        self.volume_button = QPushButton("🔊")
        self.refresh_button = QPushButton("🔄")
        self.remove_button = QPushButton("🗑")
        
        # Set button tooltips
        self.volume_button.setToolTip("Volume")
        self.refresh_button.setToolTip("Refresh Library")
        self.remove_button.setToolTip("Remove Selected")
        
        # Set object names for specific styling
        self.play_button.setObjectName("playButton")
        self.volume_button.setObjectName("volumeButton")
        
        # Create sliders
        self.volume_slider = QSlider(Qt.Orientation.Vertical)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setFixedHeight(100)
        
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

        # Update volume slider setup
        self.volume_slider = QSlider(Qt.Orientation.Vertical)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setFixedHeight(100)
        self.volume_slider.setStyleSheet("""
            QSlider::groove:vertical {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                        stop:0 #4CAF50,
                                        stop:0.5 #FFC107,
                                        stop:1 #F44336);
                width: 4px;
                border-radius: 2px;
            }
            QSlider::handle:vertical {
                background: white;
                height: 10px;
                width: 10px;
                margin: 0 -3px;
                border-radius: 5px;
            }
            QSlider::sub-page:vertical {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                        stop:0 rgba(76, 175, 80, 0.5),
                                        stop:0.5 rgba(255, 193, 7, 0.5),
                                        stop:1 rgba(244, 67, 54, 0.5));
                border-radius: 2px;
            }
        """)
        
        # Create volume popup with proper styling
        self.volume_popup = QWidget(self)
        self.volume_popup.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.volume_popup.setStyleSheet("""
            QWidget {
                background-color: rgba(45, 46, 50, 0.95);
                border-radius: 10px;
            }
        """)
        
        # Setup volume popup layout
        volume_popup_layout = QVBoxLayout(self.volume_popup)
        volume_popup_layout.setContentsMargins(10, 10, 10, 10)
        volume_popup_layout.addWidget(self.volume_slider)
        self.volume_popup.setFixedSize(40, 120)
        self.volume_popup.hide()
        
        # Apply styles
        self._apply_styles()
        
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
        
        # Add panels to main layout with proper proportions
        main_layout.addWidget(left_panel, 1)  # 1 part width
        main_layout.addWidget(right_panel, 2)  # 2 parts width

    def _create_left_panel(self):
        """Create and return the left panel with playlist controls"""
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(20, 20, 20, 20)
        
        # Add buttons at the top
        top_buttons_layout = QHBoxLayout()
        
        # Create and style add folder button
        add_folder_btn = QPushButton("+ Add Music Folder")
        add_folder_btn.clicked.connect(self.add_folder)
        
        # Add all buttons to the top layout
        top_buttons_layout.addWidget(add_folder_btn)
        top_buttons_layout.addWidget(self.refresh_button)
        top_buttons_layout.addWidget(self.remove_button)
        
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
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(20)
        
        # Add album art and track info
        album_container = self._create_album_container()
        right_layout.addWidget(album_container)
        
        # Add progress controls
        slider_container = self._create_slider_container()
        right_layout.addWidget(slider_container)
        
        # Add playback controls
        controls_container = self._create_controls_container()
        right_layout.addWidget(controls_container)
        
        return right_panel

    def _create_album_container(self):
        """Create container for album art and track info"""
        album_container = QWidget()
        album_layout = QVBoxLayout(album_container)
        album_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Add album art
        album_layout.addWidget(self.album_art, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Add track information
        track_info_layout = QVBoxLayout()
        track_info_layout.setSpacing(5)
        track_info_layout.addWidget(self.track_title, alignment=Qt.AlignmentFlag.AlignCenter)
        track_info_layout.addWidget(self.track_artist, alignment=Qt.AlignmentFlag.AlignCenter)
        album_layout.addLayout(track_info_layout)
        
        return album_container

    def _create_slider_container(self):
        """Create container for progress slider and time labels"""
        slider_container = QWidget()
        slider_layout = QVBoxLayout(slider_container)
        slider_layout.setSpacing(5)
        
        self.progress_slider.setFixedHeight(20)
        slider_layout.addWidget(self.progress_slider)
        
        # Time labels layout
        time_layout = QHBoxLayout()
        time_layout.addWidget(self.time_current)
        time_layout.addStretch()
        time_layout.addWidget(self.time_total)
        slider_layout.addLayout(time_layout)
        
        return slider_container

    def _create_controls_container(self):
        """Create container for playback control buttons"""
        controls_container = QWidget()
        controls_layout = QHBoxLayout(controls_container)
        controls_layout.setSpacing(30)
        controls_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        controls_layout.addWidget(self.prev_button)
        controls_layout.addWidget(self.play_button)
        controls_layout.addWidget(self.next_button)
        controls_layout.addWidget(self.volume_button)
        
        return controls_container

    def setup_connections(self):
        """Set up all signal connections"""
        # Connect buttons
        self.play_button.clicked.connect(self.toggle_playback)
        self.next_button.clicked.connect(self.play_next)
        self.prev_button.clicked.connect(self.play_previous)
        self.volume_button.clicked.connect(self.show_volume_popup)
        self.refresh_button.clicked.connect(self.refresh_library)
        self.remove_button.clicked.connect(self.remove_selected)
        
        # Connect sliders
        self.volume_slider.valueChanged.connect(self.change_volume)
        self.progress_slider.sliderMoved.connect(self.seek)
        
        # Connect playlist
        self.playlist_widget.itemDoubleClicked.connect(self.playlist_double_clicked)
        self.genre_combo.currentTextChanged.connect(self.genre_changed)
        
        # Connect genre selector
        self.genre_combo.currentTextChanged.connect(self.genre_changed)
        
        # Connect media player signals
        self.player.positionChanged.connect(self.position_changed)
        self.player.durationChanged.connect(self.duration_changed)

        # Set initial volume to 50%
        self.audio_output.setVolume(0.5)

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
                qimg = QImage.fromData(QByteArray(album_art_data))
                pixmap = QPixmap.fromImage(qimg)
                scaled_pixmap = pixmap.scaled(300, 300, Qt.AspectRatioMode.KeepAspectRatio, 
                                            Qt.TransformationMode.SmoothTransformation)
                self.album_art.setPixmap(scaled_pixmap)
                self.album_art.setStyleSheet("""
                    QLabel {
                        background-color: #2d2e32;
                        border-radius: 20px;
                        min-width: 300px;
                        min-height: 300px;
                    }
                """)
            except Exception as e:
                print(f"Error setting album art: {e}")
                self.set_default_album_art()
        else:
            self.set_default_album_art()
        if folder_path in self.scanned_folders:
            return
            
        supported_formats = ['.mp3', '.wav', '.flac', '.m4a', '.ogg']
        
        for root, _, files in os.walk(folder_path):
            genre = os.path.basename(root)
            
            if genre not in self.genres:
                self.genres[genre] = []
                self.genre_combo.addItem(genre)
            
            existing_paths = {track['path'] for track in self.genres[genre]}
            
            for file in files:
                if any(file.lower().endswith(fmt) for fmt in supported_formats):
                    file_path = os.path.join(root, file)
                    
                    if file_path in existing_paths:
                        continue
                    
                    self.genres[genre].append({
                        'path': file_path,
                        'title': os.path.splitext(file)[0],
                        'genre': genre
                    })
        
        self.scanned_folders.add(folder_path)
        self.update_playlist()
        self.save_data()

    def add_folder(self):
        """Open file dialog to select and add a music folder"""
        folder = QFileDialog.getExistingDirectory(self, "Select Music Folder")
        if folder:
            self.scan_folder(folder)

    def extract_metadata(self, file_path):
        """Extract metadata from audio file including artist and album art"""
        try:
            audio = File(file_path)
            
            # Default metadata
            metadata = {
                'title': os.path.splitext(os.path.basename(file_path))[0],
                'artist': 'Unknown Artist',
                'album_art': None
            }
            
            if audio is not None:
                # Extract title and artist based on file type
                if hasattr(audio, 'tags'):
                    # MP3 (ID3) tags
                    if 'TIT2' in audio:
                        metadata['title'] = str(audio['TIT2'])
                    if 'TPE1' in audio:
                        metadata['artist'] = str(audio['TPE1'])
                    # Extract album art
                    if 'APIC:' in audio:
                        metadata['album_art'] = audio['APIC:'].data
                    elif 'APIC' in audio:
                        metadata['album_art'] = audio['APIC'].data
                elif hasattr(audio, 'metadata'):
                    # FLAC/OGG metadata
                    if 'title' in audio.metadata[0]:
                        metadata['title'] = str(audio.metadata[0]['title'][0])
                    if 'artist' in audio.metadata[0]:
                        metadata['artist'] = str(audio.metadata[0]['artist'][0])
                    # Extract album art from FLAC/OGG
                    if hasattr(audio, 'pictures') and audio.pictures:
                        metadata['album_art'] = audio.pictures[0].data
            
            return metadata
        except Exception as e:
            print(f"Error extracting metadata from {file_path}: {e}")
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
                qimg = QImage.fromData(QByteArray(album_art_data))
                pixmap = QPixmap.fromImage(qimg)
                
                # Scale the pixmap while maintaining aspect ratio
                scaled_pixmap = pixmap.scaled(
                    300, 300,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                
                # Create a new pixmap with fixed size and rounded corners
                display_pixmap = QPixmap(300, 300)
                display_pixmap.fill(Qt.GlobalColor.transparent)
                
                # Set the scaled image
                self.album_art.setPixmap(scaled_pixmap)
                self.album_art.setStyleSheet("""
                    QLabel {
                        background-color: #2d2e32;
                        border-radius: 20px;
                        min-width: 300px;
                        min-height: 300px;
                    }
                """)
            except Exception as e:
                print(f"Error setting album art: {e}")
                self.set_default_album_art()
        else:
            self.set_default_album_art()

    def play_track(self, index):
        """Play the track at the given index"""
        if 0 <= index < len(self.current_playlist):
            self.current_index = index
            track = self.current_playlist[index]
            
            # Set the source and play
            self.player.setSource(QUrl.fromLocalFile(track['path']))
            self.player.play()
            self.play_button.setText("⏸")
            
            # Update track information with fallbacks
            self.track_title.setText(track.get('title', os.path.splitext(os.path.basename(track['path']))[0]))
            self.track_artist.setText(track.get('artist', 'Unknown Artist'))
            
            # Update album art
            if 'album_art' in track and track['album_art']:
                self.update_album_art(track['album_art'])
            else:
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
        # Connect buttons
        self.play_button.clicked.connect(self.toggle_playback)
        self.next_button.clicked.connect(self.play_next)
        self.prev_button.clicked.connect(self.play_previous)
        
        # Connect sliders
        self.progress_slider.sliderMoved.connect(self.seek)
        
        # Connect playlist
        self.playlist_widget.itemDoubleClicked.connect(self.playlist_double_clicked)
        
        # Connect genre selector
        self.genre_combo.currentTextChanged.connect(self.genre_changed)
        
        # Connect media player signals
        self.player.positionChanged.connect(self.position_changed)
        self.player.durationChanged.connect(self.duration_changed)
        
        # Volume control connections
        self.volume_button.clicked.connect(self.show_volume_popup)
        self.volume_slider.valueChanged.connect(self.change_volume)

        # Set initial volume
        initial_volume = 50  # 50% volume
        self.audio_output.setVolume(initial_volume / 100.0)
        self.volume_slider.setValue(initial_volume)
        self.change_volume(initial_volume)
        
    def show_volume_popup(self):
        """Show the volume slider popup near the volume button"""
        if self.volume_popup.isVisible():
            self.volume_popup.hide()
            return
            
        # Get the global position of the volume button
        button_pos = self.volume_button.mapToGlobal(self.volume_button.rect().topLeft())
        
        # Position the popup above the button
        popup_x = button_pos.x() - self.volume_popup.width()//2 + self.volume_button.width()//2
        popup_y = button_pos.y() - self.volume_popup.height() - 10
        
        # Set initial volume value
        self.volume_slider.setValue(int(self.audio_output.volume() * 100))
        
        self.volume_popup.move(popup_x, popup_y)
        self.volume_popup.show()
        
        # Hide popup when clicked outside
        QTimer.singleShot(100, self.start_volume_popup_monitor)
        
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
        """Change the volume and update the icon"""
        volume = value / 100.0
        self.audio_output.setVolume(volume)
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