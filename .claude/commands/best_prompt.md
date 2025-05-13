# Best Coding Prompts

## Problem-Based
"Implement a function that finds the longest palindromic substring in a given string. Explain your approach and its time complexity."

## Context-Rich
"Create a React component for a dropdown menu with the following requirements:
- Support for both single and multi-select options
- Keyboard navigation (arrow keys, enter, escape)
- Search functionality for filtering options
- Accessibility compliance (ARIA attributes)
- Mobile-friendly design
Include any necessary props and state management."

## Step-Guidance
"Build a simple REST API for a todo list application:
1. First, design the database schema
2. Then implement the CRUD endpoints
3. Add input validation and error handling
4. Finally, implement authentication using JWT
Use Express.js and MongoDB for this task."

## Test-Driven
"Write a function that converts a number to its Roman numeral representation. Your code should pass these test cases:
- 1 → 'I'
- 4 → 'IV'
- 9 → 'IX'
- 14 → 'XIV'
- 58 → 'LVIII'
- 1994 → 'MCMXCIV'"

## Refactoring
"Refactor this code to improve readability and performance:
```javascript
function doStuff(arr) {
  let res = [];
  for (let i = 0; i < arr.length; i++) {
    for (let j = 0; j < arr.length; j++) {
      if (i !== j && arr[i] + arr[j] === 10) {
        res.push([i, j]);
      }
    }
  }
  return res;
}
```"

## Edge Cases
"Implement a URL parser that extracts the protocol, domain, path, query parameters, and fragment from a URL. Handle these edge cases:
- URLs with and without protocol
- URLs with and without www prefix
- URLs with various TLDs (.com, .org, .co.uk)
- Query parameters with special characters
- Fragments with paths"

## Progressive Enhancement
"Start by writing a basic implementation of a binary search tree. Then progressively add:
1. Insert and search methods
2. Deletion method
3. Balancing algorithm
4. Tree traversal methods (inorder, preorder, postorder)
5. Serialization and deserialization methods"