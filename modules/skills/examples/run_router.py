from eaon.context_router import load_skill_context, route_task


def main() -> None:
    tasks = [
        'Analyze this repository structure and tell me what files are relevant.',
        'Fix this traceback: Attribute app not found in module eaon_council_server.',
        'Design the architecture for a local-first digital twin agent.',
        'Create an FTTH digital twin model for NVT and trench segments.',
        'Summarize the project decisions from this long conversation.',
    ]

    for task in tasks:
        decision = route_task(task)
        context = load_skill_context(decision)

        print('=' * 80)
        print(f'TASK: {task}')
        print(f'SELECTED SKILL: {decision.selected_skill}')
        print(f'REASON: {decision.reason}')
        print(f'CONTEXT BUDGET: {decision.context_budget}')
        print(f'FILES LOADED: {decision.files_to_load}')
        print(f'LOADED CONTEXT CHARS: {len(context)}')


if __name__ == '__main__':
    main()
