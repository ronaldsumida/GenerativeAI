from flask import Flask, render_template, request, jsonify
from io import BytesIO
import base64
from PIL import Image
from openai import OpenAI

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/inpaint', methods=['POST'])
def inpaint():
    """
    Expects a JSON payload with two keys:
      - "image": A data URL (base64 PNG) of the original image.
      - "mask": A data URL (base64 PNG) of the same image, but with transparent pixels where inpainting is desired.
      
    The function locates the transparent area in the mask, determines a 1024x1024 region
    (centered on the transparent pixels), sends that region to DALL-E for inpainting, and then
    pastes the returned region back onto the original image.
    """
    data = request.get_json(force=True)
    image_data = data.get('image')
    mask_data = data.get('mask')
    if not image_data or not mask_data:
        return jsonify({'error': 'Both "image" and "mask" data must be provided'}), 400

    # Decode the original image.
    try:
        _, image_encoded = image_data.split(',', 1)
        image_bytes = base64.b64decode(image_encoded)
    except Exception:
        return jsonify({'error': 'Invalid image data'}), 400

    # Decode the mask image.
    try:
        _, mask_encoded = mask_data.split(',', 1)
        mask_bytes = base64.b64decode(mask_encoded)
    except Exception:
        return jsonify({'error': 'Invalid mask data'}), 400

    # Open both images as RGBA.
    try:
        original_image = Image.open(BytesIO(image_bytes)).convert('RGBA')
        mask_image = Image.open(BytesIO(mask_bytes)).convert('RGBA')
    except Exception:
        return jsonify({'error': 'Could not open image or mask'}), 400

    # Both images must be the same size.
    if original_image.size != mask_image.size:
        return jsonify({'error': 'Image and mask must have the same dimensions'}), 400

    width, height = original_image.size

    # We need to extract a 1024x1024 region.
    if width < 1024 or height < 1024:
        return jsonify({'error': 'Original image must be at least 1024x1024 pixels'}), 400

    # Find the bounding box of fully transparent pixels in the mask.
    min_x, min_y = width, height
    max_x, max_y = 0, 0
    found_transparent = False

    mask_pixels = mask_image.load()
    for y in range(height):
        for x in range(width):
            r, g, b, a = mask_pixels[x, y]
            if a == 0:
                found_transparent = True
                if x < min_x: min_x = x
                if y < min_y: min_y = y
                if x > max_x: max_x = x
                if y > max_y: max_y = y

    if not found_transparent:
        return jsonify({'error': 'No transparent pixels found in mask'}), 400

    # Determine the dimensions of the transparent area.
    bbox_width = max_x - min_x + 1
    bbox_height = max_y - min_y + 1

    # If the entire transparent region cannot fit within 1024x1024, report an error.
    if bbox_width > 1024 or bbox_height > 1024:
        return jsonify({'error': 'Transparent region too large to fit in a 1024x1024 area'}), 400

    # Compute the center of the transparent bounding box.
    center_x = (min_x + max_x) // 2
    center_y = (min_y + max_y) // 2

    # Determine the top-left coordinate for the 1024x1024 region centered on the transparent area.
    region_left = center_x - 1024 // 2
    region_top = center_y - 1024 // 2

    # Adjust the region if it extends beyond the image boundaries.
    if region_left < 0:
        region_left = 0
    elif region_left + 1024 > width:
        region_left = width - 1024

    if region_top < 0:
        region_top = 0
    elif region_top + 1024 > height:
        region_top = height - 1024

    region_box = (region_left, region_top, region_left + 1024, region_top + 1024)

    # Crop the 1024x1024 region from the original and mask images.
    cropped_original = original_image.crop(region_box)
    cropped_mask = mask_image.crop(region_box)

    # Save these crops to in-memory PNG files.
    original_region_io = BytesIO()
    original_region_io.name = 'image.png'
    cropped_original.save(original_region_io, format='PNG')
    original_region_io.seek(0)

    mask_region_io = BytesIO()
    mask_region_io.name = 'mask.png'
    cropped_mask.save(mask_region_io, format='PNG')
    mask_region_io.seek(0)

    # Call DALL-E to inpaint the cropped region.
    # (Make sure your OpenAI client is set up with the proper credentials.)
    try:
        client = OpenAI()

        response = client.images.edit(
            image=original_region_io,         # original image region as a file-like object
            mask=mask_region_io,              # mask region as a file-like object
            prompt="Blend transparent regions with the background.",
            response_format='b64_json',
            size='1024x1024',
            n=1
        )

    except Exception as e:
        return jsonify({'error': f'DALL-E inpainting failed: {str(e)}'}), 500

    # Extract the inpainted image from the response.
    try:
        inpainted_b64 = response.data[0].b64_json
        inpainted_bytes = base64.b64decode(inpainted_b64)
        inpainted_region = Image.open(BytesIO(inpainted_bytes)).convert('RGBA')
    except Exception:
        return jsonify({'error': 'Failed to decode inpainted image from DALL-E'}), 500

    # Overlay the inpainted 1024x1024 region onto the original image.
    original_image.paste(inpainted_region, box=(region_left, region_top))

    # Save the modified image to an in-memory PNG.
    output_io = BytesIO()
    original_image.save(output_io, format='PNG')
    output_io.seek(0)
    output_base64 = base64.b64encode(output_io.getvalue()).decode('utf-8')
    result_data_url = 'data:image/png;base64,' + output_base64

    return jsonify({'image': result_data_url})

if __name__ == '__main__':
    app.run(debug=True)
