# Percentage Experiment

This folder contains three generator configurations you can copy and reuse with either your ShEx or SHACL shape file.

The important part is that the same TOML can be used for both languages because the generator auto-detects the schema format when `schema_format` is omitted.
For the lossy SHACL case, the config sets `schema_format = "Shacl"` explicitly so the repo's `.shacl` example is handled correctly.

## Cases

- `triple_validity_clean.toml`: intended to reach 100% triple validity on a supported shape.
- `triple_validity_not_100.toml`: intended to produce some invalid triples on the same shape.
- `shape_translation_loss_lossy_shacl.toml`: intended to show translation loss with a SHACL schema that contains unsupported constructs.

## How to run

Use the same config file with your ShEx version of the shape or your SHACL version of the same shape.

Examples:

```bash
cargo run -q -p rudof_generate -- --config rudof_generate/examples/percentage_experiment/triple_validity_clean.toml --schema examples/simple.shex --entities 1
cargo run -q -p rudof_generate -- --config rudof_generate/examples/percentage_experiment/triple_validity_not_100.toml --schema examples/simple.shex --entities 1
cargo run -q -p rudof_generate -- --config rudof_generate/examples/percentage_experiment/shape_translation_loss_lossy_shacl.toml --schema rudof_generate/examples/conformance_cases/lossy_shapes.shacl --entities 1
```

## Notes

- Keep the input shape content equivalent between the ShEx and SHACL versions.
- `triple_validity_clean.toml` and `triple_validity_not_100.toml` only differ in generation settings.
- `shape_translation_loss_lossy_shacl.toml` uses the same generation settings as the clean case, but it is meant to be run with a lossy SHACL schema.
- If you want to keep a SHACL file with a `.ttl` extension instead of `.shacl`, you can remove the explicit `schema_format` from the loss case and rely on auto-detection.
- Output paths are under `target/percentage_experiment/` so the results stay grouped together.
