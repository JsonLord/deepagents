# Using the mcp-rest-api Server

The `deepagents-cli` tool is integrated with the `mcp-rest-api` server, which provides access to a variety of tools, including `huggingface_tools`.

## Automatic Server Management

When you install the `deepagents-cli` tool, the `mcp-rest-api` server is automatically cloned and built. When you run the `deepagents-cli`, the server is automatically started if it is not already running.

## Accessing the Server

The `mcp-rest-api` server runs on `http://localhost:8000`. You can use the `http_request` tool to send requests to the server.

### Example

To get a list of available tools, you can use the following command:

```
/http_request http://localhost:8000/tools
```

This will return a list of all the tools that are available through the `mcp-rest-api` server.

## Using Hugging Face Tools

The `mcp-rest-api` server provides access to a number of `huggingface_tools`. To use these tools, you will need to send a POST request to the `/tools/{tool_name}` endpoint.

### Example

To use the `summarization` tool, you would send a POST request to `http://localhost:8000/tools/summarization` with a JSON body containing the text you want to summarize.

```json
{
  "text": "This is a long piece of text that you want to summarize."
}
```

The server will then return a summary of the text.
