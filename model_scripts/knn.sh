#!/usr/bin/env bash
alg="knn"
params_set=( \
	'{"k": 1}' \
	'{"k": 10}' \
	'{"k": 100}' \
	'{"k": 1000}' \
)

for params in "${params_set[@]}"
do
	results_subdir=$(date +"%m-%d-%Y_%s")
	./run_main.sh "${alg}" "${params}" "${results_subdir}"
done

echo "====================================="
echo "DONE"
echo "====================================="
