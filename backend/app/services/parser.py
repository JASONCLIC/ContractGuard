from ..nlp.pipeline import run_pipeline


def parse_contract_text(contract_text: str, contract_type: str = "labor", progress_callback=None):
    return run_pipeline(contract_text, contract_type, progress_callback=progress_callback)
