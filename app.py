import streamlit as st
import time
import pandas as pd
import os
from PIL import Image
import re
import glob
import zipfile
from io import BytesIO
from pygoogle_image import image as pi

# Function to sanitize filenames by removing invalid characters
def sanitize_filename(name):
    return re.sub(r'[<>:"/\\|?*]', '', name)

# Set up the app title
st.title("Image Downloader from CSV/Excel")

# Add custom CSS for gradient background
st.markdown(
    """
    <style>
    body {
        background: linear-gradient(135deg, #ffcccc, #ffe6e6);
        color: #333333;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Sidebar uploader and instructions card
st.sidebar.header("Upload CSV or Excel File")
st.sidebar.write("Upload a CSV or Excel file that contains **two columns**: 'ID' and 'Name'. These are required to download and save images.")
uploaded_file = st.sidebar.file_uploader("Upload your CSV/Excel file", type=["csv", "xlsx", "xls"])

# Instruction card about the columns in the CSV file
st.sidebar.info("**Instructions:** The uploaded file must contain two columns:\n\n"
                "1. **ID**: Unique identifier for each image.\n"
                "2. **Name**: The name to be used for downloading the image.\n\n"
                "The image will be resized to 380x380 pixels and saved with the ID as the filename.")

# Ensure the file contains the correct columns and process it
if uploaded_file is not None:
    # Check file type and read the data
    if uploaded_file.name.endswith(".csv"):
        data = pd.read_csv(uploaded_file)
    elif uploaded_file.name.endswith((".xlsx", ".xls")):
        data = pd.read_excel(uploaded_file)
        # Convert Excel to CSV format internally for consistent processing
        csv_path = "temp_file.csv"
        data.to_csv(csv_path, index=False)
        data = pd.read_csv(csv_path)  # Reload the CSV for uniform processing
        os.remove(csv_path)  # Clean up the temporary CSV

    # Show a preview of the uploaded file
    st.write("Uploaded File Preview:")
    st.dataframe(data.head())

    # Check if the required columns are present
    if 'ID' in data.columns and 'Name' in data.columns:
        st.success("The file contains the required columns: 'ID' and 'Name'")

        # Set parameters for image downloading
        image_folder = "images"
        if not os.path.exists(image_folder):
            os.makedirs(image_folder)

        delay_between_requests = 5  # Time delay between requests
        batch_size = 200  # Number of images to process in one batch
        delay_between_batches = 20  # Pause between batches

        # If the user presses the "Start Image Download" button
        if st.button("Start Image Download"):
            ids = data['ID']
            names = data['Name']

            # Initialize a counter for the images
            image_counter = 0
            total_images = len(ids)

            # Create a progress bar in the main screen
            progress_bar = st.progress(0)
            status_text = st.empty()

            # Loop through the names and IDs for image processing
            for idx, (id_, name) in enumerate(zip(ids, names)):
                # Skip rows with empty or invalid ID/Name
                if pd.isnull(id_) or pd.isnull(name) or id_ == 0 or str(id_).strip() == "" or str(name).strip() == "":
                    st.warning(f"Skipping ID: {id_}, Name: {name} (Empty or invalid)")
                    continue

                # Sanitize the name to remove invalid characters
                sanitized_name = sanitize_filename(str(name))

                # Download the image using the sanitized name as a keyword
                pi.download(keywords=f"{sanitized_name}", limit=1)

                # Find the most recently downloaded image (assuming '.jpg' extension)
                image_files = glob.glob("*.jpg")
                if image_files:
                    downloaded_image = max(image_files, key=os.path.getctime)

                    # Open the image and resize it
                    img = Image.open(downloaded_image)
                    img = img.resize((380, 380))

                    # Save the image with the ID as the filename in the 'images' folder
                    new_image_path = os.path.join(image_folder, f"{id_}.jpg")
                    img.save(new_image_path)

                    # Remove the original downloaded image
                    os.remove(downloaded_image)

                # Increment the image counter
                image_counter += 1

                # Update the progress bar and status text
                progress_percentage = (image_counter / total_images)
                progress_bar.progress(progress_percentage)
                status_text.text(f"Processed {image_counter}/{total_images} images.")

                # Add a delay between requests to avoid rate-limiting
                time.sleep(delay_between_requests)

                # Pause after processing a batch of images
                if image_counter % batch_size == 0:
                    st.warning(f"Processed {image_counter} images. Pausing for {delay_between_batches} seconds...")
                    time.sleep(delay_between_batches)

            # Create a ZIP file with all the processed images
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for foldername, subfolders, filenames in os.walk(image_folder):
                    for filename in filenames:
                        file_path = os.path.join(foldername, filename)
                        zip_file.write(file_path, os.path.relpath(file_path, image_folder))
            zip_buffer.seek(0)

            # Provide a link to download the ZIP file
            st.success(f"All images have been downloaded, resized, and saved in the '{image_folder}' folder!")
            st.download_button(
                label="Download ZIP file",
                data=zip_buffer,
                file_name="images.zip",
                mime="application/zip"
            )
    else:
        st.error("The uploaded file must contain 'ID' and 'Name' columns.")
