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

function colourise(element, classification) {
  element.classList.remove('high', 'medium', 'low');
  if (!classification) return;
  if (classification.includes('High')) element.classList.add('high');
  else if (classification.includes('Medium')) element.classList.add('medium');
  else element.classList.add('low');
}
