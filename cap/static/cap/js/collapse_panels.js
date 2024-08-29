document.addEventListener('DOMContentLoaded', function () {
    const wis2NodeCheckbox = document.querySelector('#id_wis2_node');
    const metadataPanel = document.querySelector('[data-contentpath="metadata_id"]');
    const internalTopicPanel = document.querySelector('[data-contentpath="internal_topic"]');

    function toggleFields() {
        if (!metadataPanel || !internalTopicPanel) {
            return;
        }
        // Show metadata panel if WIS2 node is checked, otherwise show internal topic panel
        metadataPanel.style.display = wis2NodeCheckbox.checked ? 'block' : 'none';
        internalTopicPanel.style.display = wis2NodeCheckbox.checked ? 'none' : 'block';
    }

    if (wis2NodeCheckbox) {
        wis2NodeCheckbox.addEventListener('change', toggleFields);
        toggleFields();
    } else {
        console.error('wis2NodeCheckbox not found');
    }
});
