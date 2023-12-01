(function() {
    function isScriptGeneratedElement(element) {
        // Check if the ID matches the pattern for script-generated borders or labels
        const isBorder = element.id.startsWith('item_id_border__');
        const isLabel = element.id.startsWith('item_id_label__');
        return isBorder || isLabel;
    }
  
    const allElements = document.querySelectorAll('body *');
    allElements.forEach(element => {
        if (isScriptGeneratedElement(element)) {
            element.parentNode.removeChild(element);
        }
    });
  })();
