from PIL import Image

# Replace with your jpeg path
img = Image.open('/Users/garrettburr/Documents/Armis/Dev/Projects/AudioPlayerApp/Icons/wave-icon.png')
# Convert to sizes commonly used for icons
icon_sizes = [(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)]
img.save('icon.ico', sizes=icon_sizes)