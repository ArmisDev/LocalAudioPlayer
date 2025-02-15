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
        # Create all buttons
        self.prev_button = QPushButton("Previous")
        self.play_button = QPushButton("Play")
        self.next_button = QPushButton("Next")
        self.shuffle_button = QPushButton("Shuffle")
        
        # Create sliders
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(50)
        
        # Create other UI elements
        self.playlist_widget = QListWidget()
        self.track_info = QLabel("No track playing")
        self.genre_combo = QComboBox()
        self.genre_combo.addItem("All Genres")
        for genre in self.genres.keys():
            self.genre_combo.addItem(genre)

    def init_ui(self):
        """Initialize the UI layout"""
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Add genre selector
        main_layout.addWidget(self.genre_combo)
        
        # Add playlist
        main_layout.addWidget(self.playlist_widget)
        
        # Add track info
        main_layout.addWidget(self.track_info)
        
        # Add progress slider
        main_layout.addWidget(self.progress_slider)
        
        # Add control buttons
        controls_layout = QHBoxLayout()
        controls_layout.addWidget(self.prev_button)
        controls_layout.addWidget(self.play_button)
        controls_layout.addWidget(self.next_button)
        controls_layout.addWidget(self.shuffle_button)
        main_layout.addLayout(controls_layout)
        
        # Add volume control
        volume_layout = QHBoxLayout()
        volume_label = QLabel("Volume:")
        volume_layout.addWidget(volume_label)
        volume_layout.addWidget(self.volume_slider)
        main_layout.addLayout(volume_layout)
        
        # Create menu bar
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        add_folder_action = file_menu.addAction("Add Folder")
        add_folder_action.triggered.connect(self.add_folder)

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
            self.play_button.setText("Play")
        else:
            self.player.play()
            self.play_button.setText("Pause")

    def play_track(self, index):
        if 0 <= index < len(self.current_playlist):
            self.current_index = index
            track = self.current_playlist[index]
            self.player.setSource(QUrl.fromLocalFile(track['path']))
            self.player.play()
            self.play_button.setText("Pause")
            self.track_info.setText(f"Playing: {track['title']}")

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