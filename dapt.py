#!/usr/bin/env python3

import os
import sys
import argparse
import json

import apt

class AptWrapper:
    @staticmethod
    def refresh():
        return apt.Cache()

    @staticmethod
    def get_installed_packages():
        cache = AptWrapper.refresh()

        packages = []
        for pkg in cache:
            if pkg.is_installed:
                packages.append(pkg.name)

        return packages


    @staticmethod
    def commit_changes(changes):
        cache = AptWrapper.refresh()

        for pkg in changes["install"]:
            if pkg not in cache:
                print(f"Warning: Package {pkg} not found in cache.", file=sys.stderr)
                return False
            print(f"Mark for install {pkg}")

            pkg = cache[pkg]
            pkg.mark_install(from_user=True)

        for pkg in changes["remove"]:
            if pkg not in cache:
                print(f"Warning: Package {pkg} not found in cache.", file=sys.stderr)
                return False

            pkg = cache[pkg]
            if pkg.is_installed:
                pkg.mark_delete()
            else:
                print(f"Package {pkg} is not installed; skipping removal.", file=sys.stderr)

            print(f"Mark for remove {pkg}")


        try:
            print("Committing changes...")
            cache.commit()
        except Exception as err:
            print(f"Error committing changes: {err}", file=sys.stderr)
            sys.exit(1)


class State:

    @staticmethod
    def patch(state, plan):
        new = []
        new.extend(state)

        for pkg in plan["install"]:
            new.append(pkg)

        for pkg in plan["remove"]:
            new.remove(pkg)

        return list(dict.fromkeys(new))


    @staticmethod
    def write(state_dir, state_file, state):
        print(f"Write state: {state}")
        try:
            os.makedirs(state_dir, exist_ok=True)
            with open(state_file, "w") as f:
                json.dump(state, f, indent=2)
            print(f"State file has been written to {state_file}")
            return True
        except Exception as err:
            print(f"Error writing state file: {err}", file=sys.stderr)
            sys.exit(1)

    @staticmethod
    def diff(desired, current):
       return [item for item in desired if item not in current]

    @staticmethod
    def read_state(state):
        if os.path.exists(state):
            try:
                with open(state, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError as err:
                print(f"Error parsing state file: {err}", file=sys.stderr)
                sys.exit(1)
        else:
            print("Error: No state file found. Please run the 'init' command first.", file=sys.stderr)
            sys.exit(1)


    @staticmethod
    def build_user_declared_state(config):
        """
        Parse a configuration file using a simple custom parser.
        common:
          - ncdu
          - nslookup

        devops:
          - terraform
          - docker-ce
          - util-/now==2.40.4-5

        Returns a dict mapping section names to lists of package specifications.
        """
        state = []
        try:
            with open(config, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue  # Skip empty lines and comments.
                    if line.startswith("---"):
                        continue  # Ignore YAML document separator.
                    if line.endswith(":"):
                        continue
                    elif line.startswith("-"):
                        item = line.lstrip("-").strip()
                        if item:
                            state.append(item)
                    else:
                        # Ignore unexpected lines.
                        continue
        except Exception as err:
            print(f"Error reading config file: {err}", file=sys.stderr)
            sys.exit(1)
        return state



class DApt:
    def __init__(self, config):
        self.config_file = config
        self.state_dir = os.path.expanduser("~/.local/state/decapt")
        self.state_file = os.path.join(self.state_dir, "state.json")
        self.plan_file = os.path.join(self.state_dir, "plan.json")


    def init(self):
        if os.path.exists(self.state_file):
            print(f"State file already exists at {self.state_file}")
            sys.exit(0)

        state = []
        State.write(state_dir = self.state_dir,
                    state_file = self.state_file,
                    state = state)
        return


    def plan(self):
        declared_state = State.build_user_declared_state(self.config_file)
        print(f"User declared state: {declared_state}")

        current_state = State.read_state(self.state_file)
        print(f"Current state: {current_state}")

        plan = {}
        plan["install"] = State.diff(declared_state, current_state)
        plan["remove"] = State.diff(current_state, declared_state)
        print(f"Install:  {" ".join(plan["install"])}")
        print(f"Remove: {" ".join(plan["remove"])}")

        try:
            with open(self.plan_file, "w") as f:
                json.dump(plan, f, indent=2)
        except Exception as err:
            print(f"Error writing plan file: {err}", file=sys.stderr)
            sys.exit(1)
        print(f"Plan written to {self.plan_file}\n")
        print(json.dumps(plan, indent=2))


    def apply(self):
        current_state = State.read_state(self.state_file)
        print(f"Current state: {current_state}")

        if not os.path.exists(self.plan_file):
            print("Error: Plan file not found. Please run the 'plan' command first.", file=sys.stderr)
            sys.exit(1)
        try:
            with open(self.plan_file, "r") as f:
                plan = json.load(f)
        except json.JSONDecodeError as err:
            print(f"Error parsing plan file: {err}", file=sys.stderr)
            sys.exit(1)

        if not plan:
            print("No changes to apply.")
            sys.exit(0)

        AptWrapper.commit_changes(plan)
        print("All changes have been applied.")

        new_state = State.patch(current_state, plan)

        State.write(state_dir=self.state_dir,
                    state_file = self.state_file,
                    state = new_state)

        pass



def main():
    parser = argparse.ArgumentParser(
        description="Declarative Debian apt package manager using an AptWrapper with python-apt API"
    )
    parser.add_argument("command", choices=["init", "plan", "apply"],
                        help="Command to execute: init, plan, or apply")
    parser.add_argument("--config", default="dapt.conf",
                        help="Path to configuration file (default: decapt.conf)")
    args = parser.parse_args()

    dapt = DApt(config = args.config)

    if args.command == "init":
        dapt.init()
    elif args.command == "plan":
        dapt.plan()
    elif args.command == "apply":
        dapt.apply()


if __name__ == "__main__":
    main()
