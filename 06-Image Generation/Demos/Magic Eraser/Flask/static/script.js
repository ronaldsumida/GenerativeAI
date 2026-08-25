// Get references to DOM elements
const canvas = document.getElementById('photoCanvas');
const ctx = canvas.getContext('2d');
const loadButton = document.getElementById('loadButton');
const inpaintButton = document.getElementById('inpaintButton');
const saveButton = document.getElementById('saveButton');
const fileInput = document.getElementById('fileInput');
const overlay = document.getElementById('overlay');

let offscreenCanvas = null; // Holds the full-resolution image once loaded
let offscreenCtx = null;

let originalWidth = 0;
let originalHeight = 0;
let scale = 1;            // Scale factor: displayed size / original size

let isDrawing = false;    // Whether the left mouse button is pressed
let hasModified = false;  // Tracks if at least one pixel has been erased

// NEW: Variable to store the original unmodified image (as a PNG data URL)
let originalImageDataURL = null;

// Create a custom eraser cursor (32px circle)
function createEraserCursor() {
  const cursorCanvas = document.createElement('canvas');
  const size = 32;
  cursorCanvas.width = size;
  cursorCanvas.height = size;
  const cctx = cursorCanvas.getContext('2d');

  cctx.clearRect(0, 0, size, size);
  cctx.beginPath();
  cctx.arc(size / 2, size / 2, size / 2 - 1, 0, Math.PI * 2);
  cctx.strokeStyle = 'black';
  cctx.lineWidth = 2;
  cctx.stroke();
  return cursorCanvas.toDataURL();
}

// Set the cursor based on whether a photo is loaded.
function updateCanvasCursor() {
  if (offscreenCanvas) {
    const cursorURL = createEraserCursor();
    // Set the custom eraser cursor with a hotspot at the center.
    canvas.style.cursor = `url(${cursorURL}) 16 16, auto`;
  } else {
    // Use the default cursor when no photo is loaded.
    canvas.style.cursor = 'default';
  }
}

/**
 * Update the canvas size.
 * If a photo has been loaded (offscreenCanvas exists), the canvas is sized based on its dimensions.
 * Otherwise, a white placeholder is drawn with a 4:3 aspect ratio.
 * In either case, the canvas width fills the viewport minus 32px margins on left and right.
 */
function updateCanvasSize() {
  // Maximum available width: viewport width minus 64px (32px each side)
  const maxWidth = window.innerWidth - 64;
  let origW, origH;
  
  if (offscreenCanvas) {
    // A photo has been loaded; use its original dimensions.
    origW = originalWidth;
    origH = originalHeight;
  } else {
    // Use a placeholder with a 4:3 aspect ratio.
    origW = maxWidth;
    origH = maxWidth * 3 / 4;
  }
  
  // Determine maximum available height.
  const controls = document.getElementById('controls');
  const controlsHeight = controls ? controls.offsetHeight + 20 : 100;
  const maxHeight = window.innerHeight - 40 - controlsHeight;
  
  // Calculate the scale factor.
  let computedScale = Math.min(maxWidth / origW, maxHeight / origH);
  if (offscreenCanvas) {
    // Never upscale a loaded photo.
    computedScale = Math.min(computedScale, 1);
  }
  scale = computedScale;
  const displayWidth = origW * scale;
  const displayHeight = origH * scale;
  
  // Resize and clear the canvas.
  canvas.width = displayWidth;
  canvas.height = displayHeight;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  
  if (offscreenCanvas) {
    // Draw the loaded photo.
    ctx.drawImage(offscreenCanvas, 0, 0, originalWidth, originalHeight, 0, 0, displayWidth, displayHeight);
  } else {
    // Draw the white placeholder.
    ctx.fillStyle = 'white';
    ctx.fillRect(0, 0, displayWidth, displayHeight);
    
    // Set up vertical centering for the plus sign and prompt text.
    ctx.fillStyle = "rgba(0,0,0,0.5)";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    
    // Define font sizes and spacing.
    const plusFontSize = 100;    // Plus sign is 100px (twice as large)
    const textFontSize = 28;
    const spacing = -16;           // Reduced vertical space between plus sign and text (8px)
    const groupHeight = plusFontSize + spacing + textFontSize;
    const groupTop = (displayHeight - groupHeight) / 2;  // Top of the group
    
    // Draw the plus sign, centered horizontally within the group.
    const plusCenterY = groupTop + plusFontSize / 2;
    ctx.font = `bold ${plusFontSize}px Roboto`;
    ctx.fillText("+", displayWidth / 2, plusCenterY);
    
    // Draw the prompt text below the plus sign.
    const textCenterY = groupTop + plusFontSize + spacing + textFontSize / 2;
    ctx.font = `${textFontSize}px Roboto`;
    ctx.fillText("Click here to load a photo", displayWidth / 2, textCenterY);
  }
  
  // Make sure the canvas is visible once it has been sized.
  canvas.style.display = "block";
  canvas.style.visibility = "visible";  // <-- Newly added: reveal canvas after sizing
  // Update the cursor based on whether a photo is loaded.
  updateCanvasCursor();
}

// Eraser function: turns pixels transparent using "destination-out".
function drawAt(clientX, clientY) {
  if (!offscreenCanvas) return;
  const rect = canvas.getBoundingClientRect();
  // Mouse position relative to canvas.
  const x = clientX - rect.left;
  const y = clientY - rect.top;
  // Convert to original image coordinates.
  const origX = x / scale;
  const origY = y / scale;
  // The displayed eraser radius is 16px; in original coordinates:
  const origRadius = 16 / scale;

  // Set composite mode to "destination-out" to erase (make transparent).
  offscreenCtx.globalCompositeOperation = 'destination-out';
  offscreenCtx.beginPath();
  offscreenCtx.arc(origX, origY, origRadius, 0, Math.PI * 2);
  offscreenCtx.fill();
  // Restore the default composite mode.
  offscreenCtx.globalCompositeOperation = 'source-over';

  // Redraw the visible canvas.
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(offscreenCanvas, 0, 0, originalWidth, originalHeight, 0, 0, canvas.width, canvas.height);

  // Always enable the Inpaint button whenever any pixels are erased.
  hasModified = true;
  inpaintButton.disabled = false;
  // Ensure the Save button remains disabled until inpainting.
  saveButton.disabled = true;
}

// --- Event Listeners ---

// "Load Photo" button: trigger the hidden file input.
loadButton.addEventListener('click', () => {
  fileInput.click();
});

// Allow clicking the placeholder canvas to trigger file input when no photo is loaded.
canvas.addEventListener('click', (e) => {
  // Only act if no photo is loaded.
  if (!offscreenCanvas && e.button === 0) {
    fileInput.click();
  }
});

// When a file is selected...
fileInput.addEventListener('change', (event) => {
  const file = event.target.files[0];
  if (!file) return;
  
  const reader = new FileReader();
  reader.onload = function(e) {
    const img = new Image();
    img.onload = function() {
      // Store the original image dimensions.
      originalWidth = img.width;
      originalHeight = img.height;

      // Create an offscreen canvas with full-resolution image data.
      offscreenCanvas = document.createElement('canvas');
      offscreenCanvas.width = originalWidth;
      offscreenCanvas.height = originalHeight;
      offscreenCtx = offscreenCanvas.getContext('2d');
      // Draw the image normally.
      offscreenCtx.clearRect(0, 0, originalWidth, originalHeight);
      offscreenCtx.drawImage(img, 0, 0);

      // NEW: Save the original image as a PNG data URL.
      originalImageDataURL = offscreenCanvas.toDataURL('image/png');

      // Update the visible canvas.
      updateCanvasSize();
      updateCanvasCursor();
      
      // Reset modification state.
      hasModified = false;
      inpaintButton.disabled = true;
      saveButton.disabled = true;
    };
    img.src = e.target.result;
  };
  reader.readAsDataURL(file);

  // Clear the file input value so that the same file can be loaded again if desired.
  fileInput.value = '';
});

// Mouse events on the canvas for erasing.
canvas.addEventListener('mousedown', (e) => {
  // Only allow erasing when a photo is loaded.
  if (!offscreenCanvas) return;
  if (e.button !== 0) return; // Only for left-click.
  isDrawing = true;
  drawAt(e.clientX, e.clientY);
});

canvas.addEventListener('mousemove', (e) => {
  if (isDrawing) {
    drawAt(e.clientX, e.clientY);
  }
});

canvas.addEventListener('mouseup', (e) => {
  if (e.button !== 0) return;
  isDrawing = false;
});

canvas.addEventListener('mouseleave', () => {
  isDrawing = false;
});

// Update canvas size on window resize.
window.addEventListener('resize', updateCanvasSize);

// "Inpaint" button: Upload the edited image for processing.
inpaintButton.addEventListener('click', () => {
  // Disable the Inpaint button and show the modal overlay to prevent duplicate requests.
  inpaintButton.disabled = true;
  overlay.style.display = 'block';
  
  // Create the mask from the offscreen canvas (which now has transparent pixels).
  const maskDataURL = offscreenCanvas.toDataURL('image/png');
  
  // Send both the original image and the mask to the server.
  fetch('/inpaint', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      image: originalImageDataURL,  // Originally loaded image (or the result of previous inpainting)
      mask: maskDataURL             // Modified image with transparent pixels.
    })
  })
  .then(response => response.json())
  .then(data => {
    if (data.image) {
      // Load the returned image.
      const newImg = new Image();
      newImg.onload = function() {
        // Update the offscreen canvas with the new image.
        originalWidth = newImg.width;
        originalHeight = newImg.height;
        offscreenCanvas.width = originalWidth;
        offscreenCanvas.height = originalHeight;
        offscreenCtx.clearRect(0, 0, originalWidth, originalHeight);
        offscreenCtx.drawImage(newImg, 0, 0);
        
        // Update originalImageDataURL so that subsequent inpaintings use the new image.
        originalImageDataURL = offscreenCanvas.toDataURL('image/png');

        // Redraw the visible canvas.
        updateCanvasSize();
        // After inpainting, enable the Save button.
        saveButton.disabled = false;
      };
      newImg.src = data.image;
    }
    else if (data.error) {
      // Show the error message returned from the server, with a
      // small delay to allow the overlay to disappear.
      setTimeout(() => {
        alert(data.error);
      }, 100);
    }
    overlay.style.display = 'none';
  })
  .catch(error => {
      // Show the error message returned from the server, with a
      // small delay to allow the overlay to disappear.
      setTimeout(() => {
      alert(error);
    }, 100);

    // Re-enable input on error.
    inpaintButton.disabled = false;
    overlay.style.display = 'none';
  });
});

// "Save Photo" button: Download the edited image.
saveButton.addEventListener('click', () => {
  if (!offscreenCanvas) return;
  const dataURL = offscreenCanvas.toDataURL('image/png');

  // Create a temporary anchor element to trigger the download.
  const link = document.createElement('a');
  link.href = dataURL;
  link.download = 'edited_photo.png';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  // Disable Save until further edits.
  saveButton.disabled = true;
});

// Initialize the placeholder and custom cursor when the page loads.
updateCanvasSize();
updateCanvasCursor();
