# Reading an unreadable image

When the user-provided image cannot be read, try these distinct available methods before asking the user to transcribe it:

1. Inspect the original image directly at its available resolution.
2. Inspect the relevant region after cropping, enlarging, or applying an appropriate readability enhancement. Preserve the original and verify any inferred text against it.
3. Extract text using an available OCR engine, then compare its output with the image. Treat OCR output as uncertain until checked.

Count an earlier attempt toward its matching method. If a method outside these three failed, assess all three and carry out each available, authorized method. Record the observed result of each attempt. Mark a method that is unavailable or unauthorized as NOT_RUN and state the limitation. Request transcription only after all three methods were attempted and failed.
