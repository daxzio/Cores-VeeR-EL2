#!/bin/bash

set -eu
set -o pipefail

if [ -v CI ]
then
  set -x

  apt update
  apt install -y xz-utils

  # XZ compresses .info files A LOT better than GZIP, e.g., 9.4MB vs 175MB.
  tar acf ${SIM}_coverage_single_data.tar.xz info_files_$SIM
  ls info_files_$SIM
fi

DB_COUNT=`ls info_files_$SIM | sed 's#_[^_]*.info##' | sort | uniq | wc -l`

# Filter out lockstep and el2_regfile_if modules if DCLS tests are not enabled
if [ -v DCLS_ENABLE ]
then
    _filter_out=''
else
    _filter_out='--filter-out (lockstep|el2_regfile_if)'
fi

# Source path transformations are needed before merging to have matching paths in `.desc` files.
find info_files_$SIM -name '*.info' -exec info-process transform \
    --strip-file-prefix '.*Cores-VeeR-EL2/' \
    --filter 'design/' $_filter_out \
    {} \;

if [ $SIM = verilator ]
then
    # Split branch and line before merging to have correct data in `.desc` files.
    for FILE in info_files_$SIM/*_branch.info
    do
        mv $FILE temp.info
        python3 .github/scripts/split_info.py temp.info --branch >$FILE
        python3 .github/scripts/split_info.py temp.info --line >${FILE%%_branch.info}_line.info
        rm temp.info
    done
fi

for TYPE in branch line toggle
do
    _sort_opt=''
    _transform_extra_opts=''
    if [ $SIM = verilator ] && [ $TYPE = toggle ]
    then
        _sort_opt=--sort-brda-names
        _transform_extra_opts='--set-block-ids --add-two-way-toggles --add-missing-brda-entries'
    fi

    info-process merge --output coverage_${TYPE}_$SIM.info $_sort_opt \
        --test-list tests_${TYPE}_$SIM.desc --test-list-strip coverage_,_$TYPE.info \
        info_files_$SIM/*_$TYPE.info

    info-process transform --normalize-hit-counts $_transform_extra_opts coverage_${TYPE}_$SIM.info
done

rm -rf info_files_$SIM

if [ -z "${GITHUB_HEAD_REF}" ]; then
        # We're in merge triggered run
        export BRANCH=$GITHUB_REF_NAME
else
        # We're in PR triggered run
        export BRANCH=$GITHUB_HEAD_REF
fi
export COMMIT=$GITHUB_SHA

# Add config.json template, "datasets" will be generated by info-process.
cat <<END >config.json
{
  "title": "VeeR EL2 coverage dashboard",
  "commit": "$COMMIT",
  "branch": "$BRANCH",
  "repo": "cores-veer-el2",
  "timestamp": "`date +"%Y-%m-%dT%H:%M:%S.%3N%z"`",
  "additional": {
    "db_count": "$DB_COUNT",
    "run_id": "$GITHUB_RUN_ID"
  }
}
END

_out_dir=data_$SIM
info-process pack --output $_out_dir --config config.json \
    --coverage-files *_$SIM.info --description-files *_$SIM.desc
rm config.json *_$SIM.info *_$SIM.desc

# add logo
cp docs/dashboard-styles/assets/chips-alliance-logo-mono.svg $_out_dir/logo.svg

cat $_out_dir/config.json

echo "Coverage data ready to be packaged in $PWD/$_out_dir"
