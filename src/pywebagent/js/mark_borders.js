(function() {
    function getXPathForElement(element) {
        // Check if the element is the body, if so, return the XPath for body
        if (element.tagName === 'BODY') {
            return '/html/body';
        }
    
        // Initialize an array to store the path parts
        const paths = [];
    
        // Iterate up the DOM tree
        for (; element && element.nodeType === Node.ELEMENT_NODE; element = element.parentNode) {
            let index = 0;
            let hasFollowingSibling = false;
    
            // Iterate over previous siblings to calculate the index
            for (let sibling = element.previousSibling; sibling; sibling = sibling.previousSibling) {
                if (sibling.nodeType === Node.DOCUMENT_TYPE_NODE) {
                    continue;
                }
                if (sibling.nodeName === element.nodeName) {
                    index++;
                }
            }
    
            // Check for following siblings with the same tag name
            for (let sibling = element.nextSibling; sibling && !hasFollowingSibling; sibling = sibling.nextSibling) {
                if (sibling.nodeName === element.nodeName) {
                    hasFollowingSibling = true;
                }
            }
    
            // Build the XPath part for this element
            const tagName = element.nodeName.toLowerCase();
            const pathIndex = (index || hasFollowingSibling) ? `[${index + 1}]` : '';
            paths.splice(0, 0, tagName + pathIndex);
        }
    
        return paths.length ? '/' + paths.join('/') : null;
    }    

  function createLabel(rect, id) {
      const label = document.createElement('div');
      let labelLeft = rect.left - 12; // Your original calculation
      if (labelLeft < 0) {
          labelLeft = 0;
      }
  
      Object.assign(label.style, {
          position: 'absolute',
          color: 'white',
          backgroundColor: 'green',
          fontSize: '15.5px',
          padding: '2px 4px',
          zIndex: '10000',
          pointerEvents: 'none',
          top: `${rect.top + 2}px`, // rect.top < 20 ? `${rect.bottom + 2}px` : `${rect.top - 16}px`,
          left: `${labelLeft}px`,
          opacity: '0.8',
          //fontWeight: 'bold', // Makes the text bold
        //   border: '2px solid red', // Red border
        //   textShadow: ' -1px -1px 0 black, 1px -1px 0 black, -1px 1px 0 black, 1px 1px 0 black' // Red border effect around text

      });
      label.id = `item_id_label__${id}`;
      label.textContent = id.toString();
      document.body.appendChild(label);
  }

  function getIntersectionRect(rect, rect2) {
    const intersectionRect = {
        top: Math.max(rect.top, rect2.top),
        left: Math.max(rect.left, rect2.left),
        right: Math.min(rect.right, rect2.right),
        bottom: Math.min(rect.bottom, rect2.bottom)
    };
    intersectionRect.width = intersectionRect.right - intersectionRect.left;
    intersectionRect.height = intersectionRect.bottom - intersectionRect.top;
    return intersectionRect;
  }

  // Checks if rects of one element is contained in another element
  function isRectContainedInElement(element, element2) {
    const rect = element.getBoundingClientRect();
    const rect2 = element2.getBoundingClientRect();
    const intersectionRect = getIntersectionRect(rect, rect2);
    return (intersectionRect.width >= 0.9 * rect2.width 
        && intersectionRect.height >= 0.9 * rect2.height);
  }

  function isPrioritisedElement(elem) {
    return ['INPUT', 'SELECT', 'A', 'BUTTON', 'TEXTAREA'].includes(elem.tagName) || elem.onclick;
  }

  function createBorder(element, id) {
      let rect = element.getBoundingClientRect();
      const topElement = document.elementFromPoint(rect.left, rect.top);
      if (topElement) {
        const rect2 = topElement.getBoundingClientRect();
        const intersectionRect = getIntersectionRect(rect, rect2);
        // If intersection exists, use it
        if (intersectionRect.width > 1 && intersectionRect.height > 1) {
            rect = intersectionRect;
        }
    }
      const border = document.createElement('div');
      const pos = rect;
      const eps = 2;
      Object.assign(border.style, {
          position: 'absolute',
          border: '2px solid green',
          width: `${rect.width + eps}px`,
          height: `${rect.height + eps}px`,
          left: `${pos.left - eps}px`,
          top: `${pos.top - eps}px`,
          zIndex: '9999',
          pointerEvents: 'none'
      });
      border.id = `item_id_border__${id}`; // Assign a unique ID to the border
      document.body.appendChild(border);
      createLabel(rect, id);
  }

  function isElementVisible(element) {
      const style = window.getComputedStyle(element);
      return !(style.display === 'none' || style.visibility === 'hidden' ||
               element.offsetWidth === 0 || element.offsetHeight === 0 || 
               element.getClientRects().length === 0);
  }

  function isElementAccessible(element) {
    const rect = element.getBoundingClientRect();
    if (rect.width < 2 || rect.height < 2) {
      return false;
    }

    function AccessibleFromLoc(element, x, y) {
        const topElement = document.elementFromPoint(x, y);
        if (topElement === null) {
            // console.log('topElement is null');
            return false;
        }
        if (topElement !== element && !topElement.contains(element)) {
            // console.log('topElement does not contain element', topElement, element);
            return false;
        }
        // if direct child of topElement, then accessible

        return true;
    }

    return (AccessibleFromLoc(element, rect.left, rect.top) ) 
        || AccessibleFromLoc(element, rect.right, rect.top) 
        || AccessibleFromLoc(element, rect.left, rect.bottom) 
        || AccessibleFromLoc(element, rect.right, rect.bottom) 
        || AccessibleFromLoc(element, rect.left + rect.width / 2, rect.top + rect.height / 2);
  }

  const markedElements = [];
  const allElements = document.querySelectorAll('body *');

  allElements.forEach(element => {
    // Skip if this element is a child of an already marked element (unless it is a prioritised element (button, select etc.)))
    // Skip also elements of already intersecting elements
    remove_containing_element = false;
    containing_element_index = markedElements.findIndex(e => e.contains(element));
    intersecting_element_index = markedElements.findIndex(e => isRectContainedInElement(e, element));

    if (containing_element_index !== -1 || intersecting_element_index !== -1) {
        if (containing_element_index !== -1) {
            containing_element = markedElements[containing_element_index];
            if ((isPrioritisedElement(element)) && !isPrioritisedElement(containing_element)) {
                remove_containing_element = true;
                console.log("removing element by dom tree hirarchy", containing_element, "because of element", element);
            } else {
                return;
            }
        } else if (intersecting_element_index !== -1) {
            intersecting_element = markedElements[intersecting_element_index];

            if ((isPrioritisedElement(element)) && !isPrioritisedElement(intersecting_element)) {
                remove_containing_element = true;
                console.log("removing element by intersection", intersecting_element, "because of element", element);
            } else {
                return;
            }
        }
    }

      const rect = element.getBoundingClientRect();
      if (rect.width < document.documentElement.clientWidth && rect.height < document.documentElement.clientHeight) {

        cursor = window.getComputedStyle(element).cursor;

        const centerX = rect.left;
        const centerY = rect.top;
        const topElement = document.elementFromPoint(centerX, centerY);
        cursor_from_point = 'n/a'
        if (topElement) {
            cursor_from_point =  window.getComputedStyle(topElement).cursor;
        }

        if (['pointer', 'hand', 'text'].includes(cursor) && ['pointer', 'auto', 'hand', 'text'].includes(cursor_from_point)) {

              if (isElementVisible(element) && isElementAccessible(element)) {
                if (remove_containing_element) {
                    markedElements.splice(containing_element_index, 1);
                }

                markedElements.push(element);
            }
      }
    }

  });

  // createBorder(element, counter) for all elements
  markedElementsMetadata = [];
  let counter = 0;  // Changed from outside the script at browser.py
  for (let i = 0; i < markedElements.length; i++) {
    const element = markedElements[i];
    let originalLabel = element.getAttribute('aria-label');
    let newLabel = `item_id__${counter}__`;

    if (originalLabel && originalLabel.includes('item_id__')) {
        originalLabel = originalLabel.replace(/item_id__\d+__/, '').trim();
    }

    if (originalLabel) {
        newLabel = `${originalLabel} ${newLabel}`;
    }  
    element.setAttribute('aria-label', newLabel); 
    createBorder(element, counter);
    markedElementsMetadata.push({
        id: counter, 
        tag: element.tagName, 
        class: element.className, 
        xpath: getXPathForElement(element),
        html: element.outerHTML, // Adding the HTML of the element
        element: element, // Store the actual element
        old_aria_label: originalLabel
    });
    counter++;
  }

  return markedElementsMetadata;
})();