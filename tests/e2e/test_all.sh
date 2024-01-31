file=${1:-TB\ Guru\ testing\ cases.xlsx}
set -x
set -e

export $(cat ../env.txt | grep -v "#" | xargs)
export PYTHONPATH=../../:../../src
python3 e2e_cli.py copy-conversations --file "$file"
python3 generate_from_golden_test_set.py
python3 overall_call_generator.py
python3 e2e_cli.py delete-test-conversations
python3 generated_golden_test_set_calling/overall_e2e_calling.py
python3 e2e_cli.py copy-test-conversations
python3 generate_from_golden_test_set.py
pytest ./generated_golden_test_set_calling/* --self-contained-html --html=report.html



set +x
