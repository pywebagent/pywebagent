import argparse
from pywebagent import act

def main(args):
    return act(
        args.url,
        args.task,
        **args.kwargs
    )

    
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, type=str, help="URL to act on")
    parser.add_argument("--task", required=True, type=str, help="Task to perform")
    parser.add_argument("--kwargs", required=False, type=str, help="Task arguments", default={})
    args = parser.parse_args()
    args.kwargs = eval(args.kwargs)
    status, output = main(args)
    print("Status:", status)
    print("Output:", output)
