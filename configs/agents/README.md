## Some configs can be changed

Because of cost, resources and only purpose for learning, modify the following configurations appropriately.

### All agent

- `model_name`: `gpt-4o-mini`, `gpt-4o`, ...
- `model_provider`: Now only models from [Openrouter](https://openrouter.ai/models?q=claude), always keep `~` or
  `openrouter`

### Planner agent

- `max_subtasks`: max number of subtasks that would be broken from entered TASK.

### Retriever agent

- `n_docs`: number of documents retrieved for input query

### Coding agent

It is the central agent, that will generate scripts. So it can be backed end by better model such `gpt-4o`, but more
expensive.

- `fix_error_attempts`: max number of times to fix one error. If exceed the program will be stopped.

### Critic agent

- `max_critics`: number of critics the agent can point out.

### Verification agent

- `verification_attempts`: max number of attempts to fix critic by this agent

### User agent

Use no model, just typed input from user.