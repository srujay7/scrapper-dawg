This document will help you extract brand from an amazon PDP by looking for "Top highlights" section of the product page 



The selected element (a.a-expander-header.a-declarative.a-expander-section-header.a-link-section-expander.a-size-medium) has the text content "Top highlights", which directly identifies it as the header for the "top highlights" section.

Here are a few ways to identify this section:

Using the text content (most robust for this specific case): You can identify the header element by its text content. This is often reliable for specific sections like "Top highlights" which are unlikely to change their visible text.
javascript

const topHighlightsHeader = Array.from(document.querySelectorAll('a.a-expander-header'))
  .find(el => el.innerText.trim() === 'Top highlights');

if (topHighlightsHeader) {
  console.log('Found Top highlights header:', topHighlightsHeader);
  // The section content would typically be a sibling or child of this header
  const topHighlightsSection = topHighlightsHeader.closest('.a-expander-header').nextElementSibling;
  console.log('Found Top highlights section:', topHighlightsSection);
}
Use code snippets with caution

Using a specific CSS selector (if available): If the "Top highlights" section itself has a unique ID or a more specific class that isn't shared by other sections, that would be the most direct way to select it. Based on the provided information, the header has a specific class combination: a.a-expander-header.a-declarative.a-expander-section-header.a-link-section-expander.a-size-medium You can use this selector to target the header. To get the actual content section, you would typically look for a sibling element that follows this header, often within a common parent.
Using aria-label or other accessibility attributes: Check if the element or its related content has aria-label, aria-labelledby, or similar attributes that clearly define its purpose. These are excellent for identification and accessibility.
Inspecting surrounding elements: Look at the parent (span.a-declarative) and sibling elements. Sometimes, a unique ID or class on a parent element can help scope your selector to a particular section of the page.
Based on the information, the most direct way to identify the header for the "Top highlights" section is by its text content combined with its existing CSS classes. To identify the section content, you would then target the element immediately following this header, which typically contains the collapsible content.


How to find "brand" under "top highlights" on amazon pdp


You're looking for a reliable way to identify the "Brand" label within the "Top highlights" section. This requires combining selectors that target the "Top highlights" section itself and then drilling down to the "Brand" label.

Here's how you can approach it, considering the hierarchical structure and the specificity needed for Amazon's pages:

Understanding the structure:

From your previous query, we identified the "Top highlights" section header as a.a-expander-header with text "Top highlights". The "Brand" label is a span.a-size-base.a-text-bold element. We also know its parent is td.a-span3. The key will be to find the containing element that uniquely identifies the "Top highlights" section's content.

Deterministic Identification Strategy:

The most robust approach will involve finding the "Top highlights" section and then locating the "Brand" element within that specific section. This avoids accidentally selecting a "Brand" label from another part of the page.

Here's a JavaScript code snippet that demonstrates this:

js

function findBrandInTopHighlights() {
  // 1. Find the "Top highlights" section header
  const topHighlightsHeader = Array.from(document.querySelectorAll('a.a-expander-header'))
    .find(el => el.textContent.trim() === 'Top highlights');

  if (!topHighlightsHeader) {
    console.warn("Could not find 'Top highlights' section header.");
    return null;
  }

  // 2. Locate the content container for the "Top highlights" section.
  //    This often follows the header. It could be a sibling div.
  //    You'll need to inspect the DOM to confirm the exact structure.
  //    For Amazon, a common pattern is an expander with a content div following it.
  //    Let's assume the content is within a div with a specific class that is a sibling.
  //    You might need to adjust this selector based on actual DOM structure.
  //    A common pattern might be something like a div with class 'a-expander-content'
  //    or a table that contains the highlights.
  let topHighlightsContentContainer = null;

  // Attempt to find a direct sibling content container
  let nextSibling = topHighlightsHeader.nextElementSibling;
  while (nextSibling) {
    // Look for a common container for expanded content, e.g., an `a-expander-content`
    if (nextSibling.classList.contains('a-expander-content') || nextSibling.tagName === 'TABLE') {
      topHighlightsContentContainer = nextSibling;
      break;
    }
    // Sometimes the content is wrapped in another div which is the sibling
    if (nextSibling.querySelector('span.a-size-base.a-text-bold') && nextSibling.textContent.includes('Brand')) {
       topHighlightsContentContainer = nextSibling;
       break;
    }
    nextSibling = nextSibling.nextElementSibling;
  }

  if (!topHighlightsContentContainer) {
    console.warn("Could not find the content container for 'Top highlights'.");
    return null;
  }

  // 3. Within the "Top highlights" content container, find the "Brand" element.
  //    We're looking for a `span` with classes `a-size-base` and `a-text-bold`
  //    and text content "Brand".
  const brandElement = Array.from(topHighlightsContentContainer.querySelectorAll('span.a-size-base.a-text-bold'))
    .find(el => el.textContent.trim() === 'Brand');

  if (brandElement) {
    console.log('Successfully identified the "Brand" label in "Top highlights" section:', brandElement);
    // You can then access its parent (`td.a-span3`) or the actual brand value (its sibling).
    const brandValueElement = brandElement.closest('td').nextElementSibling;
    console.log('Brand value element:', brandValueElement);
    return {
      brandLabel: brandElement,
      brandValue: brandValueElement
    };
  } else {
    console.warn("Could not find the 'Brand' label within the 'Top highlights' section.");
    return null;
  }
}

// Execute the function
// const data = findBrandInTopHighlights(); // For use within executeJavaScript
Use code snippets with caution

Explanation:

topHighlightsHeader: This step reliably finds the interactive header for the "Top highlights" section by looking for an <a> tag with the specific classes and matching its text content.
topHighlightsContentContainer: This is the crucial part that might require slight adjustment depending on the exact HTML structure of Amazon's product pages. After finding the header, you need to navigate to its sibling element that contains the actual "Top highlights" content (e.g., a div.a-expander-content or a table). The provided code offers a basic way to iterate through siblings and check for common container classes.
brandElement: Once inside the correct content container, you can then search for the span.a-size-base.a-text-bold element that has "Brand" as its text. This ensures you're getting the "Brand" from the correct section.
brandValueElement: To get the actual brand name (e.g., "Apple", "Samsung"), you would typically look at the sibling element to the td that contains the "Brand" label.
How to use this:

You would run this JavaScript code using the executeJavaScript function. You might need to refine the topHighlightsContentContainer selection part by inspecting the live DOM of an Amazon product page to find the most consistent container for the "Top highlights" section's content.

Marker for identifying:

HTML Marker (if you control the HTML): If you were able to modify the page, the best way would be to add a unique id or a custom data-attribute to the "Brand" span or its containing td.
html

<td class="a-span3">
  <span class="a-size-base a-text-bold" data-qa="top-highlights-brand-label">Brand</span>
</td>
<td class="a-span9">
  <span>ExampleBrand</span>
</td>
Use code snippets with caution

Then you could simply select [data-qa="top-highlights-brand-label"].
CSS/JS Marker (for existing pages): The JavaScript code above effectively acts as your "marker" by providing a programmatic way to locate the element using its inherent properties and DOM relationships.