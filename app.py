from dash import Dash, html, dcc, Input, Output, State, ALL, MATCH

# Change your button IDs to use pattern-matching
def create_setup_page():
    return html.Div([
        # Use pattern-matching IDs instead of static IDs
        dcc.Input(id={"type": "setup-input", "index": "client-id"}),
        dcc.Input(id={"type": "setup-input", "index": "client-secret"}),
        dcc.RadioItems(id={"type": "setup-input", "index": "environment"}),
        html.Button("Save", id={"type": "setup-btn", "index": "save"}),
        html.Button("Test", id={"type": "setup-btn", "index": "test"}),
    ])

def create_welcome_page():
    return html.Div([
        html.Button("Connect", id={"type": "welcome-btn", "index": "connect"}),
        html.Button("Reset", id={"type": "welcome-btn", "index": "reset"}),
    ])

# Then use pattern-matching in callback
@app.callback(
    Output("main-content", "children"),
    [
        Input("url", "search"),
        Input("url", "pathname"),
        Input({"type": "setup-btn", "index": ALL}, "n_clicks"),
        Input({"type": "welcome-btn", "index": ALL}, "n_clicks"),
    ],
    [
        State({"type": "setup-input", "index": ALL}, "value"),
    ],
    prevent_initial_call=True,
)
def handle_all_interactions(search, pathname, setup_clicks, welcome_clicks, input_values):
    ctx = dash.callback_context
    # Use ctx to figure out which button was clicked
    ...