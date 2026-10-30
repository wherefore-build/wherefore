# Security

Please do not report a vulnerability in a public issue. Use GitHub's private
vulnerability reporting on this repository (Security, then "Report a
vulnerability"), and say what you found, how to reproduce it, and what it
affects.

Wherefore runs a corpus's own generators, as Python, with the permissions of
whoever runs it - in a person's checkout or in CI. Treat a `wherefore.json`
and its generators as code: run the engine only on a repository you would run
the code of.
