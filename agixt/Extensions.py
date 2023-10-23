import importlib
import os
import glob
from inspect import signature, Parameter
import logging


class Extensions:
    def __init__(self, agent_config=None, load_commands_flag: bool = True):
        self.agent_config = agent_config
        self.commands = self.load_commands() if load_commands_flag else []
        if agent_config != None:
            self.available_commands = self.get_available_commands()

    def get_available_commands(self):
        available_commands = []
        for command in self.commands:
            friendly_name, command_module, command_name, command_args = command
            if (
                "commands" in self.agent_config
                and friendly_name in self.agent_config["commands"]
            ):
                if self.agent_config["commands"][friendly_name] in ["true", True]:
                    # Add command to list of commands to return
                    available_commands.append(
                        {
                            "friendly_name": friendly_name,
                            "name": command_name,
                            "args": command_args,
                            "enabled": True,
                        }
                    )
        return available_commands

    def get_enabled_commands(self):
        return [command for command in self.available_commands if command["enabled"]]

    def get_command_args(self, command_name: str):
        return next(
            (
                command[2]
                for command in self.get_extensions()
                if command[0] == command_name
            ),
            None,
        )

    def load_commands(self):
        try:
            settings = self.agent_config["settings"]
        except:
            settings = {}
        commands = []
        command_files = glob.glob("extensions/*.py")
        for command_file in command_files:
            module_name = os.path.splitext(os.path.basename(command_file))[0]
            module = importlib.import_module(f"extensions.{module_name}")
            if issubclass(getattr(module, module_name), Extensions):
                command_class = getattr(module, module_name)(**settings)
                if hasattr(command_class, "commands"):
                    for (
                        command_name,
                        command_function,
                    ) in command_class.commands.items():
                        params = self.get_command_params(command_function)
                        # Store the module along with the function name
                        commands.append(
                            (
                                command_name,
                                getattr(module, module_name),
                                command_function.__name__,
                                params,
                            )
                        )
        # Return the commands list
        logging.debug(f"loaded commands: {commands}")
        return commands

    def get_extension_settings(self):
        settings = {}
        command_files = glob.glob("extensions/*.py")
        for command_file in command_files:
            module_name = os.path.splitext(os.path.basename(command_file))[0]
            module = importlib.import_module(f"extensions.{module_name}")
            if issubclass(getattr(module, module_name), Extensions):
                command_class = getattr(module, module_name)()
                params = self.get_command_params(command_class.__init__)
                # Remove self and kwargs from params
                if "self" in params:
                    del params["self"]
                if "kwargs" in params:
                    del params["kwargs"]
                if params != {}:
                    settings[module_name] = params
        return settings

    def get_command_params(self, func):
        params = {}
        sig = signature(func)
        for name, param in sig.parameters.items():
            if name == "self":
                continue
            params[name] = None if param.default == Parameter.empty else param.default
        return params

    def find_command(self, command_name: str):
        for name, module, function_name, params in self.commands:
            if name == command_name:
                command_function = getattr(module, function_name)
                return command_function, module, params  # Updated return statement
        return None, None, None  # Updated return statement

    def get_commands_list(self):
        self.commands = self.load_commands()
        return [command_name for command_name, _, _ in self.commands]

    async def execute_command(self, command_name: str, command_args: dict = None):
        command_function, module, params = self.find_command(command_name=command_name)
        logging.info(
            f"Executing command: {command_name} with args: {command_args}. Command Function: {command_function}"
        )
        if command_function is None:
            logging.error(f"Command {command_name} not found")
            return False
        for param in params:
            if param not in command_args:
                if param not in ["self", "kwargs"]:
                    command_args[param] = None
        args = command_args.copy()
        for param in command_args:
            if param not in params:
                del args[param]
        try:
            output = await getattr(module(), command_function.__name__)(**args)
        except Exception as e:
            output = f"Error: {str(e)}"
        logging.info(f"Command Output: {output}")
        return output

    def get_extensions(self):
        commands = []
        command_files = glob.glob("extensions/*.py")
        for command_file in command_files:
            module_name = os.path.splitext(os.path.basename(command_file))[0]
            module = importlib.import_module(f"extensions.{module_name}")
            command_class = getattr(module, module_name.lower())()
            if hasattr(command_class, "commands"):
                for command_name, command_function in command_class.commands.items():
                    params = self.get_command_params(command_function)
                    commands.append((command_name, command_function.__name__, params))
        return commands
