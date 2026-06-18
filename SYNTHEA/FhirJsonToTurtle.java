import org.hl7.fhir.r4.formats.JsonParser;
import org.hl7.fhir.r4.formats.RdfParser;
import org.hl7.fhir.r4.model.Bundle;
import org.hl7.fhir.r4.model.Resource;

import java.io.ByteArrayOutputStream;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.ArrayList;
import java.util.List;

/**
 * Converts FHIR R4 JSON resources to RDF Turtle using the official
 * org.hl7.fhir.core library (org.hl7.fhir.r4.formats.RdfParser).
 *
 * Usage:
 *   java -cp classes:validator_cli.jar FhirJsonToTurtle <in1.json> <out1.ttl> [<in2.json> <out2.ttl> ...]
 *
 * IMPORTANT: RdfParser.compose() on a Bundle only emits the Bundle envelope and
 * does NOT recurse into entry.resource (the contained clinical resources are
 * lost). Synthea exports everything as Bundles, so we unwrap each Bundle and
 * serialize every contained resource individually, which yields complete
 * FHIR-RDF (a fhir:Patient/Observation/... with all elements and values).
 *
 * All conversions run in a single JVM to avoid per-file startup overhead.
 * Exit code is the number of files that FAILED (0 == all succeeded).
 */
public class FhirJsonToTurtle {
    public static void main(String[] args) {
        if (args.length == 0 || args.length % 2 != 0) {
            System.err.println("Usage: FhirJsonToTurtle <in.json> <out.ttl> [<in.json> <out.ttl> ...]");
            System.exit(2);
        }

        JsonParser jsonParser = new JsonParser();
        int failures = 0;
        long totalResources = 0;

        for (int i = 0; i + 1 < args.length; i += 2) {
            String inPath = args[i];
            String outPath = args[i + 1];
            try (InputStream in = new FileInputStream(inPath)) {
                Resource parsed = (Resource) jsonParser.parse(in);

                // Flatten Bundles to their contained resources so the clinical
                // content is actually serialized (RdfParser drops it otherwise).
                List<Resource> resources = new ArrayList<>();
                if (parsed instanceof Bundle) {
                    for (Bundle.BundleEntryComponent e : ((Bundle) parsed).getEntry()) {
                        if (e.hasResource()) {
                            resources.add(e.getResource());
                        }
                    }
                } else {
                    resources.add(parsed);
                }

                // RdfParser.compose() closes the stream it writes to, so we
                // serialize each resource into its own buffer and append the
                // bytes to the output file (repeated @prefix lines are valid
                // Turtle and are de-duplicated when the graph is re-parsed).
                try (OutputStream out = new FileOutputStream(outPath)) {
                    for (Resource res : resources) {
                        ByteArrayOutputStream buf = new ByteArrayOutputStream();
                        new RdfParser().compose(buf, res);
                        out.write(buf.toByteArray());
                        out.write('\n');
                    }
                }
                totalResources += resources.size();
                System.out.println("OK   " + outPath + "  (" + resources.size() + " resource(s))");
            } catch (Exception e) {
                failures++;
                System.err.println("FAIL " + inPath + " : " + e.getClass().getSimpleName() + ": " + e.getMessage());
            }
        }

        int files = args.length / 2;
        System.out.println("Converted " + (files - failures) + "/" + files
                + " file(s), " + totalResources + " resource(s) total");
        System.exit(failures);
    }
}
