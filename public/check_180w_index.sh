#!/bin/bash
# Read the YuE2 copy of the 180w index. Does not open audio and does not train.
CFG=/cache/yue2_files/datasets/acctask-180w-acc-caption-cfgs
ls -lh "$CFG/pt_all_v1.txt" "$CFG/vocal_wav_all.txt" "$CFG/wav2len.txt"
wc -l "$CFG/pt_all_v1.txt"
mapfile -t lists < <(find "$CFG" -name '200w*.txt' -printf '%p\n' | head)
printf '%s\n' "${lists[@]}"
if [ "${#lists[@]}" -gt 0 ]; then
  python -c 'import json,sys; rec=json.loads(open(sys.argv[1], encoding="utf-8").readline()); inner=rec.get("v", rec);
inner=json.loads(inner) if isinstance(inner, str) else inner
print("top_keys", list(rec))
print("record_keys", list(inner) if isinstance(inner, dict) else type(inner).__name__)' "${lists[0]}"
fi
