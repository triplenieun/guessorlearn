const predButton = document.getElementById('predButton');
predButton.addEventListener('click', prediction);
predButton.disabled = true;
predButton.disabled = true;
predButton.disabled = false;

const clearButton = document.getElementById('clearButton');
clearButton
// clearButton.classList.add('highlight-effect');
// clearButton.classList.add('highlight-effect');
// clearButton.classList.remove('highlight-effect');
clearButton.addEventListener('click', () => {
    clearData(true);
});
clearButton.addEventListener('click', recommend);

// <button id="clearButton" class="btn-basic invisible">clear</button>
// <button id="predButton" class="btn-basic invisible">predict</button>