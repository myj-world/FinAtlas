const form = document.getElementById('single-form');
const batchForm = document.getElementById('batch-form');
const singleResult = document.getElementById('single-result');
const batchResult = document.getElementById('batch-result');

function formToObject(formElement) {
  const data = new FormData(formElement);
  const obj = {};
  for (const [key, value] of data.entries()) {
    obj[key] = value;
  }
  return obj;
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  singleResult.textContent = 'Screening...';
  try {
    const response = await fetch('/api/screen/single', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(formToObject(form)),
    });
    const result = await response.json();
    singleResult.textContent = JSON.stringify(result, null, 2);
    colourise(singleResult, result.classification);
  } catch (error) {
    singleResult.textContent = `Error: ${error.message}`;
  }
});

batchForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  batchResult.textContent = 'Uploading...';
  try {
    const response = await fetch('/api/screen/batch', {
      method: 'POST',
      body: new FormData(batchForm),
    });
    const result = await response.json();
    batchResult.textContent = JSON.stringify(result, null, 2);
  } catch (error) {
    batchResult.textContent = `Error: ${error.message}`;
  }
});

const loadSampleButton = document.getElementById('load-sample');
const screenSampleButton = document.getElementById('screen-sample');
const sampleResult = document.getElementById('sample-result');
let sampleRecords = [];

loadSampleButton.addEventListener('click', async () => {
  sampleResult.textContent = 'Loading sample...';
  try {
    const response = await fetch('/api/import/sample');
    const result = await response.json();
    sampleRecords = result.records || [];
    sampleResult.textContent = `Loaded ${sampleRecords.length} sample transactions.\n\n${JSON.stringify(sampleRecords, null, 2)}`;
    screenSampleButton.disabled = sampleRecords.length === 0;
  } catch (error) {
    sampleResult.textContent = `Error: ${error.message}`;
    screenSampleButton.disabled = true;
  }
});

screenSampleButton.addEventListener('click', async () => {
  if (sampleRecords.length === 0) return;
  sampleResult.textContent = 'Screening sample...';
  try {
    const response = await fetch('/api/screen/batch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(sampleRecords),
    });
    const result = await response.json();
    sampleResult.textContent = JSON.stringify(result, null, 2);
  } catch (error) {
    sampleResult.textContent = `Error: ${error.message}`;
  }
});

function colourise(element, classification) {
  element.classList.remove('high', 'medium', 'low');
  if (!classification) return;
  if (classification.includes('High')) element.classList.add('high');
  else if (classification.includes('Medium')) element.classList.add('medium');
  else element.classList.add('low');
}
