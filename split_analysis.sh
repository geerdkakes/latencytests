#!/usr/bin/env bash

csv_file=${1}

if [ ! -f "${csv_file}" ]; then
    echo "${0}: file \"${csv_file}\" does not exist"
    exit 1
fi
echo "spliting file ${csv_file}"

csv_file_extension="${csv_file##*.}"

base_csv_file="${csv_file%.*}"

echo "base filename: ${base_csv_file}"

filename_a="${base_csv_file}_a.${csv_file_extension}"
filename_b="${base_csv_file}_b.${csv_file_extension}"
filename_c="${base_csv_file}_c.${csv_file_extension}"
filename_d="${base_csv_file}_d.${csv_file_extension}"

cat /dev/null > ${filename_a}
cat /dev/null > ${filename_b}
cat /dev/null > ${filename_c}
cat /dev/null > ${filename_d}

# a: lines to keep: 1, 2, 6, 10
# b: lines to keep: 1, 2
# c: lines to keep: 1, 6
# d: lines to keep: 1, 10

a=(1 2 6 10)
b=(1 2)
c=(1 6)
d=(1 10)




counter=1
while IFS= read -r line
do
    for i in ${a[@]}; do
        if [ "${counter}" == "${i}" ] ; then
            echo "${line}" >> ${filename_a}
        fi
    done
    for i in ${b[@]}; do
        if [ "${counter}" == "${i}" ] ; then
            echo "${line}" >> ${filename_b}
        fi
    done
    for i in ${c[@]}; do
        if [ "${counter}" == "${i}" ] ; then
            echo "${line}" >> ${filename_c}
        fi
    done
    for i in ${d[@]}; do
        if [ "${counter}" == "${i}" ] ; then
            echo "${line}" >> ${filename_d}
        fi
    done
    ((counter++))
done < "${csv_file}"

echo "created file ${filename_a}"
echo "created file ${filename_b}"
echo "created file ${filename_c}"
echo "created file ${filename_d}"

echo "starting graph for original file: ${csv_file}"
./total_tests.sh -c ${csv_file} -a graph

echo "starting graph analysis for ${filename_a}."
./total_tests.sh -c ${filename_a} -a graph

echo "starting graph analysis for ${filename_b}."
./total_tests.sh -c ${filename_b} -a graph

echo "starting graph analysis for ${filename_c}."
./total_tests.sh -c ${filename_c} -a graph

echo "starting graph analysis for ${filename_d}."
./total_tests.sh -c ${filename_d} -a graph

echo "done"
