from homey import app


class PythonScriptApp(app.App):
    async def on_init(self) -> None:
        self.log("PythonScriptApp initialised")


homey_export = PythonScriptApp
