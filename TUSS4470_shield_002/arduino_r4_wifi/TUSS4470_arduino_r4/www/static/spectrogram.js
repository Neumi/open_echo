// Responsive canvas sizing and DOM caching
const canvas = document.getElementById('spectrogram');
const overlayCanvas = document.getElementById('cursor-overlay');
const overlayCtx = overlayCanvas.getContext('2d');
const cursorDepthLabel = document.getElementById('cursor-depth-label');
const yTicks = document.getElementById('y-ticks');

let sample_resolution = 1; // cm/sample, set by server
let width = window.innerWidth;
let height = window.innerHeight;
let yRangeIndex = 0;
const yRanges = [5, 10, 25, 50, 75, 100];
let yRange = yRanges[yRangeIndex];
let metersPerRow = sample_resolution / 100;
let ySamples = Math.max(1, Math.floor(yRange / metersPerRow));
let maxMeasuredDepth = 0;
let ctx, imageData;

class RunningStats {
  constructor() {
    this.n = 0;
    this.mean = 0;
    this.M2 = 0; // running sum of squares of differences
  }

  pushArray(values) {
    for (const v of values) {
      if (typeof v !== "number" || isNaN(v)) continue;
      this.n++;
      const delta = v - this.mean;
      this.mean += delta / this.n;
      const delta2 = v - this.mean;
      this.M2 += delta * delta2;
    }
  }

  meanValue() {
    return this.mean;
  }

  stdValue() {
    return this.n > 1 ? Math.sqrt(this.M2 / (this.n - 1)) : 0;
  }
}

const runningStats = new RunningStats();

function resizeCanvases() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    overlayCanvas.width = window.innerWidth;
    overlayCanvas.height = window.innerHeight;
    width = canvas.width;
    height = canvas.height;
    ctx = canvas.getContext('2d');
    imageData = ctx.createImageData(width, height);
}
window.addEventListener('resize', resizeCanvases);
resizeCanvases();

/**
 * Update sample resolution and dependent variables.
 * @param {number} newResolution
 */
function updateSampleResolution(newResolution) {
    sample_resolution = newResolution;
    metersPerRow = sample_resolution / 100;
    ySamples = Math.max(1, Math.floor(yRange / metersPerRow));
}

/**
 * Update visual range and dependent variables.
 * @param {number} newYRangeIndex
 */
function updateVisualRange(newYRangeIndex) {
    yRangeIndex = newYRangeIndex;
    yRange = yRanges[yRangeIndex];
    ySamples = Math.max(1, Math.floor(yRange / metersPerRow));
}

// --- Mapping utilities ---
/**
 * Convert y pixel to sample index.
 * @param {number} y
 * @returns {number}
 */
function yPixelToSampleIdx(y) {
    return Math.max(0, Math.min(ySamples - 1, Math.floor(y * ySamples / (height - 1))));
}
/**
 * Convert sample index to y pixel.
 * @param {number} sampleIdx
 * @returns {number}
 */
function sampleIdxToYPixel(sampleIdx) {
    return ySamples > 1 ? Math.round(sampleIdx * (height - 1) / (ySamples - 1)) : 0;
}
/**
 * Convert y pixel to depth in meters.
 * @param {number} y
 * @returns {number}
 */
function yPixelToDepth(y) {
    const sampleIdx = yPixelToSampleIdx(y);
    return Math.round(100 * sampleIdx * metersPerRow) / 100;
}
/**
 * Convert depth in meters to y pixel.
 * @param {number} depth
 * @returns {number}
 */
function depthToYPixel(depth) {
    const sampleIdx = Math.round(depth / metersPerRow);
    return sampleIdxToYPixel(sampleIdx);
}
/**
 * Convert depth in meters to sample index.
 * @param {number} depth
 * @returns {number}
 */
function depthToSampleIdx(depth) {
    return Math.round(depth / metersPerRow);
}
/**
 * Convert sample index to depth in meters.
 * @param {number} sampleIdx
 * @returns {number}
 */
function sampleIdxToDepth(sampleIdx) {
    return Math.round(100 * sampleIdx * metersPerRow) / 100;
}

// --- Overlay rendering ---
function drawCursorOverlay(y) {
    overlayCtx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
    overlayCtx.beginPath();
    overlayCtx.moveTo(0, y);
    overlayCtx.lineTo(overlayCanvas.width, y);
    overlayCtx.strokeStyle = 'orange';
    overlayCtx.lineWidth = 1;
    overlayCtx.stroke();
}

canvas.addEventListener('mousemove', function (e) {
    const y = e.clientY - overlayCanvas.getBoundingClientRect().top;
    const depthAtCursor = yPixelToDepth(y);
    cursorDepthLabel.textContent = `Cursor: ${depthAtCursor} m`;
    drawCursorOverlay(y);
});
canvas.addEventListener('mouseleave', function () {
    cursorDepthLabel.textContent = 'Cursor: -- m';
    overlayCtx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
});

// --- Spectrogram rendering ---
/**
 * Automatic gain adjustment: scale value using mean and std of most recent column.
 * @param {number} value
 * @returns {Array} RGB color
 */
function getColor(value) {
    // Center and scale value
    let high = runningStats.meanValue() + 2 * runningStats.stdValue();
    let low = runningStats.meanValue() - 2 * runningStats.stdValue();
    let scaled = (value - low) / (high - low);
    // Clamp to [0,1]
    scaled = Math.max(0, Math.min(1, scaled));
    return evaluate_cmap(scaled, "Spectral");
}

function shiftLeft(imageData) {
    const { data, width, height } = imageData;
    for (let y = 0; y < height; y++) {
        for (let x = 0; x < width - 1; x++) {
            const i = (y * width + x) * 4;
            const j = (y * width + (x + 1)) * 4;
            data[i] = data[j];
            data[i + 1] = data[j + 1];
            data[i + 2] = data[j + 2];
            data[i + 3] = data[j + 3];
        }
    }
}

let sum = 0;
let count = 0;
let diff_squared = 0;

function insertColumn(values, depth) {
    // Compute mean and std for automatic gain adjustment
    const valid = values.filter(v => typeof v === 'number');
    if (valid.length > 0) {
        runningStats.pushArray(valid);
    }
    shiftLeft(imageData);
    const x = width - 1;
    for (let y = 0; y < height; y++) {
        const sampleIdx = yPixelToSampleIdx(y);
        const value = values[sampleIdx] ? values[sampleIdx] : 0;
        const [r, g, b] = getColor(value);
        const i = (y * width + x) * 4;
        const sampleDepth = sampleIdxToDepth(sampleIdx);
        if (Math.abs(depth - sampleDepth) < metersPerRow * 1.5) {
            imageData.data[i] = 255;
            imageData.data[i + 1] = 0;
            imageData.data[i + 2] = 0;
            imageData.data[i + 3] = 255;
        } else {
            imageData.data[i] = r;
            imageData.data[i + 1] = g;
            imageData.data[i + 2] = b;
            imageData.data[i + 3] = 255;
        }
    }
    ctx.putImageData(imageData, 0, 0);
    updateAxisLabels(depth);
}

// --- WebSocket connection and events ---
const ws = new WebSocket((location.protocol==='https:'?'wss':'ws') + '://' + location.hostname + ':81/');

ws.binaryType = 'arraybuffer';
ws.onmessage = (event) => {
    const buf = event.data;
    if (!(buf instanceof ArrayBuffer)) return;
    const dv = new DataView(buf);
    let p = 0;
    if (dv.getUint8(p++) !== 0xAA) return;
    const depthIdx = (dv.getUint8(p++) << 8) | dv.getUint8(p++);
    p += 2; // temp
    p += 2; // vDrv
    const values = [];
    while (p + 1 < dv.byteLength - 1) {
        values.push(dv.getUint8(p++));
    }
    updateSampleResolution(1);
    const depth = depthIdx * (sample_resolution / 100);
    if (depth > maxMeasuredDepth) maxMeasuredDepth = depth;
    updateYRange();
    insertColumn(values, depth);
};
ws.onerror = (e) => console.error('WebSocket error:', e);
ws.onclose = () => console.warn('WebSocket closed');

// --- Y-axis range logic ---
function updateYRange() {
    if (!window.manualZoom) {
        let autoIndex = yRanges.findIndex(r => maxMeasuredDepth <= r);
        if (autoIndex === -1) autoIndex = yRanges.length - 1;
        updateVisualRange(autoIndex);
    } else {
        updateVisualRange(yRangeIndex);
    }
    updateYRangeLabel();
}

function updateYRangeLabel() {
    document.getElementById('y-range-label').textContent = `0-${yRanges[yRangeIndex]}`;
}

// --- Axis label rendering ---
function updateAxisLabels(depth) {
    const measuredDepthLabel = document.getElementById('measured-depth-label');
    measuredDepthLabel.childNodes[0].nodeValue = 'Depth: ' + Math.round(depth * 100) / 100 + 'm';

    const numYTicks = 5;
    yTicks.innerHTML = '';
    for (let i = 0; i < numYTicks; i++) {
        const sampleIdx = Math.floor(i * ySamples / (numYTicks - 1));
        const depthValue = sampleIdxToDepth(sampleIdx);
        const tick = document.createElement('div');
        tick.className = 'y-tick';
        tick.textContent = depthValue + 'm';
        const yPx = sampleIdxToYPixel(sampleIdx);
        tick.style.top = `${yPx}px`;
        yTicks.appendChild(tick);
    }
}

// --- Zoom controls ---
document.getElementById('zoom-in').addEventListener('click', function () {
    if (yRangeIndex > 0) {
        updateVisualRange(yRangeIndex - 1);
        window.manualZoom = true;
        updateYRangeLabel();
        updateAxisLabels();
    }
});
document.getElementById('zoom-out').addEventListener('click', function () {
    if (yRangeIndex < yRanges.length - 1) {
        updateVisualRange(yRangeIndex + 1);
        window.manualZoom = true;
        updateYRangeLabel();
        updateAxisLabels();
    }
});