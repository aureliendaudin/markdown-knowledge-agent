from tools.markdown_tools import (
    get_document_structure,
    read_section,
    get_headers_with_preview,
    search_in_headers
)

# Test 4: Search in headers
result = search_in_headers.invoke("regression")
print(result)
