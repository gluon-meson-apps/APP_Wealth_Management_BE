import click

from tests.e2e.copy_conversations_to_fixed_test import ConversationCopyBoy


@click.group()
def cli():
    pass

@click.command()
@click.option('--file', default="./TB Guru testing cases.xlsx", help='file path of test case xlsx')
def copy_conversations(file):
    copy_boy = ConversationCopyBoy()
    copy_boy.copy_conversations(file)

@click.command()
def delete_test_conversations():
    copy_boy = ConversationCopyBoy()
    copy_boy.delete_test_cases()

@click.command()
def copy_test_conversations():
    copy_boy = ConversationCopyBoy()
    copy_boy.copy_test_conversations_from_model_log()

if __name__ == '__main__':
    cli.add_command(copy_conversations)
    cli.add_command(copy_test_conversations)
    cli.add_command(delete_test_conversations)
    cli()
