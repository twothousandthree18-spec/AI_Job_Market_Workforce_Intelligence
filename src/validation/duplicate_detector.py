from __future__ import annotations

import pandas as pd
from rapidfuzz import fuzz


class DuplicateDetector:
    """Multi-level duplicate detection for job posting DataFrames."""

    def detect_exact(self, df: pd.DataFrame) -> dict[str, list[int]]:
        key_cols = ["source", "source_job_id"]
        present = [c for c in key_cols if c in df.columns]
        if len(present) < 2:
            return {}
        mask = df[present].notna().all(axis=1)
        valid = df[mask]
        if valid.empty:
            return {}
        groups = valid.groupby(present).indices
        return {f"{k[0]}::{k[1]}": v.tolist() for k, v in groups.items() if len(v) > 1}

    def detect_url_duplicates(self, df: pd.DataFrame) -> dict[str, list[int]]:
        if "job_url" not in df.columns:
            return {}
        non_null = df["job_url"].notna() & (df["job_url"].astype(str).str.strip() != "")
        valid = df[non_null]
        if valid.empty:
            return {}
        groups = valid.groupby("job_url").indices
        return {k: v.tolist() for k, v in groups.items() if len(v) > 1}

    def detect_content_duplicates(
        self, df: pd.DataFrame, threshold: int = 85
    ) -> list[tuple[int, int, float]]:
        """Content similarity with blocking to avoid O(n^2) on large datasets.

        Blocks by (company_name, city) to only compare records likely to be
        duplicates. Falls back to city-only blocking if company is missing.
        """
        text_cols = ["company_name", "job_title", "city"]
        present = [c for c in text_cols if c in df.columns]
        if not present:
            return []

        def _build_text(row: pd.Series) -> str:
            parts = [str(row[c]) if pd.notna(row[c]) else "" for c in present]
            return " ".join(parts).strip().lower()

        texts = df.apply(_build_text, axis=1).tolist()
        indices = df.index.tolist()

        # Build blocks by (company_name, city) for blocking
        block_col = None
        for bc in ["company_name", "city"]:
            if bc in df.columns:
                block_col = bc
                break

        if block_col and len(df) > 500:
            blocks: dict[str, list[int]] = {}
            for i, idx in enumerate(indices):
                val = df.at[idx, block_col]
                block_key = (
                    str(val).lower() if pd.notna(val) else "_none_"
                )
                if block_key not in blocks:
                    blocks[block_key] = []
                blocks[block_key].append(i)

            pairs: list[tuple[int, int, float]] = []
            for _block_key, block_indices in blocks.items():
                if len(block_indices) < 2:
                    continue
                for bi in range(len(block_indices)):
                    for bj in range(bi + 1, len(block_indices)):
                        ii = block_indices[bi]
                        ij = block_indices[bj]
                        score = fuzz.token_sort_ratio(texts[ii], texts[ij])
                        if score >= threshold:
                            pairs.append((indices[ii], indices[ij], score))
            return pairs
        else:
            pairs: list[tuple[int, int, float]] = []
            for i in range(len(texts)):
                for j in range(i + 1, len(texts)):
                    score = fuzz.token_sort_ratio(texts[i], texts[j])
                    if score >= threshold:
                        pairs.append((indices[i], indices[j], score))
            return pairs

    def mark_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["is_duplicate"] = False
        df["dup_group"] = None
        df["dup_reason"] = None

        group_counter = 0

        exact = self.detect_exact(df)
        for _key, idx_list in exact.items():
            for idx in idx_list:
                df.at[idx, "is_duplicate"] = True
                df.at[idx, "dup_group"] = group_counter
                df.at[idx, "dup_reason"] = "exact_source_id"
            group_counter += 1

        url_dups = self.detect_url_duplicates(df)
        for _url, idx_list in url_dups.items():
            already_grouped = [i for i in idx_list if df.at[i, "dup_group"] is not None]
            if already_grouped:
                min_group = min(df.at[i, "dup_group"] for i in already_grouped)
                for i in idx_list:
                    df.at[i, "is_duplicate"] = True
                    if df.at[i, "dup_group"] is None:
                        df.at[i, "dup_group"] = min_group
                        df.at[i, "dup_reason"] = "url_duplicate"
            else:
                for i in idx_list:
                    df.at[i, "is_duplicate"] = True
                    df.at[i, "dup_group"] = group_counter
                    df.at[i, "dup_reason"] = "url_duplicate"
                group_counter += 1

        content_pairs = self.detect_content_duplicates(df)
        for idx1, idx2, _score in content_pairs:
            g1 = df.at[idx1, "dup_group"]
            g2 = df.at[idx2, "dup_group"]
            if g1 is not None and g2 is not None:
                continue
            target_group = g1 if g1 is not None else (g2 if g2 is not None else group_counter)
            df.at[idx1, "is_duplicate"] = True
            df.at[idx1, "dup_group"] = target_group
            df.at[idx1, "dup_reason"] = "content_similarity"
            df.at[idx2, "is_duplicate"] = True
            df.at[idx2, "dup_group"] = target_group
            df.at[idx2, "dup_reason"] = "content_similarity"
            if g1 is None and g2 is None:
                group_counter += 1

        return df
