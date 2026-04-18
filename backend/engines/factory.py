from engines.metashape import MetashapeEngine
# from engines.webodm import WebODMEngine  <-- For the future!

def get_engine(engine_name: str, dataset_name: str, input_dir: str, output_dir: str):
    engines = {
        "metashape": MetashapeEngine,
        # "webodm": WebODMEngine
    }
    
    engine_class = engines.get(engine_name.lower())
    if not engine_class:
        raise ValueError(f"Unknown engine: {engine_name}")
        
    return engine_class(dataset_name, input_dir, output_dir)