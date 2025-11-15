# COMP-5313: Chatbot Contest 
The chatbot I used is a React-loop agent with the ability to consider the whole conversation before providing the final response.
It has a tool that retrieves documents from vector store [lakehead/faiss_v.1](vectorstores/lakehead/faiss_v.1). 

This demo works on console only and aims to test the performance of the chatbot.
## Preparation

```bash
pip install -r requirements.txt
```

## Provide environment variables
Paste [OpenRouter](https://openrouter.ai) api key to [.env file](.env) 
```yaml
OPENROUTER_API_KEY=???
```
## Usage
```bash
python main.py
```

## Prospect

There are some good results with this demo. After running ```python main```, enter question as below:
```bash
Enter your question (q to quit): information about SCHOOL OF KINESIOLOGY
```

When inspecting the conversation, you can see that it can retrieve documents as content in [link 1](https://www.lakeheadu.ca/programs/graduate/programs/masters/kinesiology/node/7260#:~:text=MSc%20in%20Kinesiology:%20Gerontology%20Specialization%20(Thesis%2Dbased)) 
and [link 2](https://csdc.lakeheadu.ca/Catalog/ViewCatalog.aspx?pageid=viewcatalog&catalogid=33&chapterid=11334&loaduseredits=True). They are very minimal 😅😅.

## Issue
If have any issue, try to debug or create a pull request.