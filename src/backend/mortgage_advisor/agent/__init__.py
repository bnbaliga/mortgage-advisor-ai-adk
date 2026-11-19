"""The ADK agent: personas, tools, policy, observer and persona routing.

`root_agent` is loaded lazily so importing a tool module does not build the agent.
`adk web src/backend` finds it as `mortgage_advisor.agent.root_agent`.
"""


def __getattr__(name):
    if name == "root_agent":
        from mortgage_advisor.agent.agent import root_agent
        return root_agent
    raise AttributeError(name)
