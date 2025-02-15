import sys
import os
import json
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QListWidget, QLabel, 
                           QSlider, QFileDialog, QComboBox)
from PyQt6.QtCore import Qt, QUrl, QTimer
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
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

    def create_ui_elements(self):
        """Create all UI elements and store them as class attributes"""
        # Set application style
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1b1e;
                color: white;
            }
            QLabel {
                color: white;
            }
            QPushButton {
                background-color: transparent;
                color: white;
                border: none;
                padding: 5px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
            QListWidget {
                background-color: #2d2e32;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 5px;
            }
            QComboBox {
                background-color: #2d2e32;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 8px;
                margin: 5px;
            }
            QSlider {
                height: 20px;
            }
            QSlider::groove:horizontal {
                background: #4a4a4a;
                height: 4px;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: white;
                width: 12px;
                height: 12px;
                border-radius: 6px;
                margin: -4px 0;
            }
        """)
        
        # Create all buttons
        self.prev_button = QPushButton("⏮")
        self.play_button = QPushButton("▶")
        self.next_button = QPushButton("⏭")
        self.shuffle_button = QPushButton("🔀")
        
        # Create sliders
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(50)
        
        # Create track information labels
        self.track_title = QLabel("No Track Playing")
        self.track_title.setStyleSheet("font-size: 24px; font-weight: bold;")
        self.track_artist = QLabel("Unknown Artist")
        self.track_artist.setStyleSheet("font-size: 16px; color: #aaaaaa;")
        
        # Create time labels
        self.time_current = QLabel("0:00")
        self.time_total = QLabel("0:00")
        
        # Create playlist and genre elements
        self.playlist_widget = QListWidget()
        self.genre_combo = QComboBox()
        self.genre_combo.addItem("All Genres")
        for genre in self.genres.keys():
            self.genre_combo.addItem(genre)
            
        # Create album art placeholder
        self.album_art = QLabel()
        self.album_art.setStyleSheet("""
            QLabel {
                background-color: #2d2e32;
                border-radius: 20px;
                min-width: 300px;
                min-height: 300px;
            }
        """)

    def init_ui(self):
        """Initialize the UI layout"""
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Left side layout (Playlist and Genre)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(20, 20, 20, 20)
        
        # Add folder button at the top
        add_folder_btn = QPushButton("+ Add Music Folder")
        add_folder_btn.clicked.connect(self.add_folder)
        add_folder_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d2e32;
                padding: 10px;
                border-radius: 10px;
            }
        """)
        left_layout.addWidget(add_folder_btn)
        
        # Add genre selector
        left_layout.addWidget(self.genre_combo)
        
        # Add playlist with a label
        playlist_label = QLabel("Playlist")
        playlist_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-top: 20px;")
        left_layout.addWidget(playlist_label)
        left_layout.addWidget(self.playlist_widget)
        
        # Right side layout (Player controls)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(20, 20, 20, 20)
        
        # Add album art
        right_layout.addWidget(self.album_art, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Add track information
        track_info_layout = QVBoxLayout()
        track_info_layout.addWidget(self.track_title, alignment=Qt.AlignmentFlag.AlignCenter)
        track_info_layout.addWidget(self.track_artist, alignment=Qt.AlignmentFlag.AlignCenter)
        right_layout.addLayout(track_info_layout)
        
        # Add progress slider and time labels
        progress_layout = QVBoxLayout()
        time_layout = QHBoxLayout()
        time_layout.addWidget(self.time_current)
        time_layout.addStretch()
        time_layout.addWidget(self.time_total)
        progress_layout.addWidget(self.progress_slider)
        progress_layout.addLayout(time_layout)
        right_layout.addLayout(progress_layout)
        
        # Add control buttons
        controls_layout = QHBoxLayout()
        controls_layout.addStretch()
        controls_layout.addWidget(self.shuffle_button)
        controls_layout.addWidget(self.prev_button)
        controls_layout.addWidget(self.play_button)
        controls_layout.addWidget(self.next_button)
        controls_layout.addStretch()
        right_layout.addLayout(controls_layout)
        
        # Add volume control
        volume_layout = QHBoxLayout()
        volume_label = QLabel("🔊")
        volume_layout.addWidget(volume_label)
        volume_layout.addWidget(self.volume_slider)
        right_layout.addLayout(volume_layout)
        
        # Add panels to main layout
        main_layout.addWidget(left_panel, 1)  # 1 part width
        main_layout.addWidget(right_panel, 2)  # 2 parts width

    def setup_connections(self):
        """Set up all signal connections"""
        # Connect buttons
        self.play_button.clicked.connect(self.toggle_playback)
        self.next_button.clicked.connect(self.play_next)
        self.prev_button.clicked.connect(self.play_previous)
        self.shuffle_button.clicked.connect(self.shuffle_playlist)
        
        # Connect sliders
        self.volume_slider.valueChanged.connect(self.change_volume)
        self.progress_slider.sliderMoved.connect(self.seek)
        
        # Connect playlist
        self.playlist_widget.itemDoubleClicked.connect(self.playlist_double_clicked)
        
        # Connect genre selector
        self.genre_combo.currentTextChanged.connect(self.genre_changed)
        
        # Connect media player signals
        self.player.positionChanged.connect(self.position_changed)
        self.player.durationChanged.connect(self.duration_changed)

    def load_saved_data(self):
        """Load saved genres and folders from config file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    self.genres = data.get('genres', {})
                    self.scanned_folders = set(data.get('folders', []))
                    
                    # Validate that all files still exist
                    for genre in list(self.genres.keys()):
                        self.genres[genre] = [
                            track for track in self.genres[genre]
                            if os.path.exists(track['path'])
                        ]
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
            # Flatten all tracks from all genres
            self.current_playlist = [track for tracks in self.genres.values() for track in tracks]
        else:
            self.current_playlist = self.genres.get(current_genre, [])
        
        for track in self.current_playlist:
            self.playlist_widget.addItem(track['title'])

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
                    
                    self.genres[genre].append({
                        'path': file_path,
                        'title': os.path.splitext(file)[0],
                        'genre': genre
                    })
        
        self.scanned_folders.add(folder_path)
        self.update_playlist()
        self.save_data()

    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Music Folder")
        if folder:
            self.scan_folder(folder)

    def toggle_playback(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            self.play_button.setText("▶")
        else:
            self.player.play()
            self.play_button.setText("⏸")

    def play_track(self, index):
        if 0 <= index < len(self.current_playlist):
            self.current_index = index
            track = self.current_playlist[index]
            self.player.setSource(QUrl.fromLocalFile(track['path']))
            self.player.play()
            self.play_button.setText("⏸")
            self.track_title.setText(track['title'])
            self.track_artist.setText(track['genre'])

    def play_next(self):
        if self.current_playlist:
            next_index = (self.current_index + 1) % len(self.current_playlist)
            self.play_track(next_index)

    def play_previous(self):
        if self.current_playlist:
            prev_index = (self.current_index - 1) % len(self.current_playlist)
            self.play_track(prev_index)

    def shuffle_playlist(self):
        if self.current_playlist:
            random.shuffle(self.current_playlist)
            self.update_playlist()

    def change_volume(self, value):
        self.audio_output.setVolume(value / 100.0)

    def seek(self, position):
        self.player.setPosition(position)

    def position_changed(self, position):
        self.progress_slider.setValue(position)

    def duration_changed(self, duration):
        self.progress_slider.setRange(0, duration)

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