

import re

import itertools

import numpy as np

import pandas as pd

from scipy.stats import entropy

import warnings

warnings.filterwarnings('ignore', category=pd.errors.DtypeWarning)

SAMPLE_SIZE = 500

SIGNATURE_SIZE = 200

UUID_RE = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$', re.I)

def normalize_scalar(v):

    if pd.isna(v):

        return ''

    s = str(v).strip().casefold()

    # Standardize obvious numeric codes while preserving non-numeric ids.

    if re.fullmatch(r'[-+]?\d+(\.0+)?', s):

        s = s.split('.')[0]

        s = s.lstrip('+')

        s = s.lstrip('0') or '0'

    return s

def smart_normalize(series):

    s = series.map(normalize_scalar)

    try:

        nums = pd.to_numeric(s, errors='coerce')

        num_mask = nums.notna()

        if num_mask.mean() > 0.8:

            s.loc[num_mask] = nums.loc[num_mask].astype(float).round(8).astype(str)

    except Exception:

        pass

    try:

        dts = pd.to_datetime(s, errors='coerce', utc=True)

        dt_mask = dts.notna()

        if dt_mask.mean() > 0.8:

            s.loc[dt_mask] = dts.loc[dt_mask].dt.strftime('%Y-%m-%dT%H:%M:%SZ')

    except Exception:

        pass

    return s

def get_id_score(col_name):

    col = col_name.lower()

    if col in ['id', 'pk', 'key', 'uuid', 'guid', 'index', '_id']:

        return 3

    if re.search(r'(_id|id|_key|key|_pk|pk)$', col):

        return 2

    if re.search(r'(id|key|code|num|no|uuid|guid)', col):

        return 1

    return 0

def get_signature(series, n=200):

    uniques = series.dropna().unique()

    if len(uniques) > n:

        try:

            uniques = np.random.choice(uniques, n, replace=False)

        except Exception:

            pass

    return set(hash(str(x)) for x in uniques)

def profile_atomic_values(vals, col_name):

    n = max(1, len(vals))

    counts = vals.value_counts(dropna=False)

    numeric_parseable = pd.to_numeric(vals, errors='coerce').notna().mean() if n else 0.0

    date_parseable = pd.to_datetime(vals, errors='coerce', utc=True).notna().mean() if n else 0.0

    avg_len = vals.str.len().mean() if n else 0.0

    uuid_like_name = 1.0 if re.search(r'(uuid|guid)', col_name.lower()) else 0.0

    uuid_valid_ratio = vals.map(lambda x: bool(UUID_RE.match(str(x)))).mean() if n else 0.0

    text_share = max(0.0, 1.0 - max(numeric_parseable, date_parseable))

    type_consistency = max(numeric_parseable, date_parseable, text_share)

    major_is_num = 1.0 if numeric_parseable >= max(date_parseable, text_share) else 0.0

    major_is_date = 1.0 if date_parseable >= max(numeric_parseable, text_share) else 0.0

    major_is_text = 1.0 if text_share >= max(numeric_parseable, date_parseable) else 0.0

    top_freq = []

    for k, v in counts.head(3).items():

        top_freq.append(f"{str(k)[:20]}:{int(v)}")

    return {

        'numeric_parseable': float(numeric_parseable),

        'date_parseable': float(date_parseable),

        'avg_len': float(avg_len),

        'uuid_like_name': float(uuid_like_name),

        'uuid_valid_ratio': float(uuid_valid_ratio),

        'invalid_uuid_rate': float(1.0 - uuid_valid_ratio) if uuid_like_name > 0 else 0.0,

        'type_consistency': float(type_consistency),

        'major_is_num': float(major_is_num),

        'major_is_date': float(major_is_date),

        'major_is_text': float(major_is_text),

        'top_freq': ' | '.join(top_freq)

    }

def extract_features(df, cols):

    is_composite = isinstance(cols, tuple)

    col_names = list(cols) if is_composite else [cols]

    n_rows = len(df)

    limit = SAMPLE_SIZE

    try:

        head = df[col_names].head(limit)

        tail = df[col_names].iloc[limit:limit * 2] if n_rows > limit * 2 else df[col_names].tail(limit)

        rand = df[col_names].sample(min(n_rows, limit), random_state=42) if n_rows > limit else df[col_names]

    except Exception:

        return None

    if is_composite:

        fn = lambda x: '||'.join(normalize_scalar(v) for v in x)

        vals_head = head.agg(fn, axis=1)

        vals_tail = tail.agg(fn, axis=1)

        vals_rand = rand.agg(fn, axis=1)

        name_str = "_".join(cols).lower()

        col_count = len(cols)

        id_score = max(get_id_score(c) for c in cols)

        profile = {

            'numeric_parseable': 0.0,

            'date_parseable': 0.0,

            'avg_len': float(vals_rand.str.len().mean()) if len(vals_rand) > 0 else 0.0,

            'uuid_like_name': 0.0,

            'uuid_valid_ratio': 0.0,

            'invalid_uuid_rate': 0.0,

            'type_consistency': 1.0,

            'major_is_num': 0.0,

            'major_is_date': 0.0,

            'major_is_text': 1.0,

            'top_freq': ''

        }

    else:

        vals_head = smart_normalize(head[cols])

        vals_tail = smart_normalize(tail[cols])

        vals_rand = smart_normalize(rand[cols])

        name_str = cols.lower()

        col_count = 1

        id_score = get_id_score(cols)

        profile = profile_atomic_values(vals_rand, cols)

    # Robustness check over head/random/tail samples.

    u_scores = []

    for v in [vals_head, vals_rand, vals_tail]:

        u_scores.append(v.nunique() / len(v) if len(v) > 0 else 0)

    if (max(u_scores) - min(u_scores)) > 0.8:

        return None

    vals = vals_rand

    n_uniq = vals.nunique()

    uniqueness = sorted(u_scores)[1]

    null_rate = df[col_names].isna().mean().max()

    dup_rate = 1.0 - uniqueness

    card_log = np.log1p(n_uniq)

    counts = vals.value_counts()

    ent = entropy(counts) if len(counts) > 0 else 0

    is_uuid_name = 1.0 if re.search(r'(uuid|guid)', name_str) else 0.0

    is_time_name = 1.0 if re.search(r'(date|time|created)', name_str) else 0.0

    # 15-D feature vector.

    feats = [

        float(uniqueness),

        float(null_rate),

        float(dup_rate),

        float(card_log),

        float(ent),

        float(profile['numeric_parseable']),

        float(profile['avg_len']),

        float(id_score),

        float(is_uuid_name),

        float(is_time_name),

        float(col_count),

        float(profile['major_is_num']),

        float(profile['major_is_date']),

        float(profile['major_is_text']),

        float(profile['type_consistency'])

    ]

    sig = get_signature(vals, SIGNATURE_SIZE)

    return feats, sig, float(profile['avg_len']), n_rows, profile, float(n_uniq)

def minimal_composite_prune(composites):

    # Drop supersets when a subset has near-identical uniqueness.

    if not composites:

        return []

    composites = sorted(composites, key=lambda x: (len(x['cols']), -x['features'][0]))

    keep = []

    for cand in composites:

        cols_set = set(cand['cols'])

        is_superset = False

        for chosen in keep:

            chosen_set = set(chosen['cols'])

            if chosen_set.issubset(cols_set):

                if abs(chosen['features'][0] - cand['features'][0]) <= 0.01:

                    is_superset = True

                    break

        if not is_superset:

            keep.append(cand)

    return keep

def process_table_file(filepath):

    try:

        try:

            df = pd.read_csv(filepath, on_bad_lines='skip', engine='pyarrow')

        except Exception:

            try:

                df = pd.read_csv(filepath, on_bad_lines='skip', low_memory=False)

            except Exception:

                df = pd.read_csv(filepath, on_bad_lines='skip', encoding='latin-1', low_memory=False)

        if df.empty:

            return []

        cols = [c for c in df.columns if not re.search(r'^(desc|note|comment|text)', c, re.I)]

        table = filepath.split('/')[-1].replace('.csv', '')

        candidates = []

        atomic_pool = []

        # 1) Atomic candidates.

        for col in cols:

            res = extract_features(df, col)

            if res:

                feats, sig, avg_len, n_rows, profile, cardinality = res

                row = {

                    'table': table,

                    'cols': (col,),

                    'features': feats,

                    'signature': sig,

                    'avg_len': avg_len,

                    'n_rows': n_rows,

                    'profile': profile,

                    'cardinality': cardinality

                }

                candidates.append(row)

                atomic_pool.append(row)

        # 2) Composite candidates from top-m by uniqueness/entropy (even if singles are weak).

        atomic_ranked = sorted(

            atomic_pool,

            key=lambda x: (x['features'][0], x['features'][4], x['features'][7]),

            reverse=True

        )

        top_m = [x['cols'][0] for x in atomic_ranked[:min(12, len(atomic_ranked))]]

        composites = []

        for r in range(2, 4):

            for c_cols in itertools.combinations(top_m, r):

                res = extract_features(df, c_cols)

                if res:

                    feats, sig, avg_len, n_rows, profile, cardinality = res

                    if feats[0] > 0.80:

                        composites.append({

                            'table': table,

                            'cols': c_cols,

                            'features': feats,

                            'signature': sig,

                            'avg_len': avg_len,

                            'n_rows': n_rows,

                            'profile': profile,

                            'cardinality': cardinality

                        })

        candidates.extend(minimal_composite_prune(composites))

        return candidates

    except Exception as e:

        print(f"  WARN: Failed to process {filepath}: {e}")

        return []

