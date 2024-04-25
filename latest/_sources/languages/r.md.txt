# R Interface

---

## Installation

```{note}
Mac users have reported issues when using a copy of R installed from [conda-forge](https://conda-forge.org/). If you encounter an issue, you may need to use R from the official [R project website](https://www.r-project.org/) or a system package manager like `brew`.
```

### From inside R

While TinyStan is not available on CRAN, you can install the R package from the source code
using the `remotes` package:

```R
remotes::install_github("https://github.com/WardBrian/tinystan", subdir="clients/R")
```

To install a specific version of TinyStan you can use the argument `ref`,
for example, {{ "`ref=\"VERSION\"`".replace("VERSION", most_recent_release) }}.

The first time you compile a model, the TinyStan source code for your current version
will be downloaded and placed in :file:`~/.tinystan/`.
If you prefer to use a source distribution of TinyStan, consult the following section.

Note that the system pre-requisites from the [Getting Started guide](../getting-started.rst)
are still required and will not be automatically installed by this method.

### From Source

This assumes you have followed the [Getting Started guide](../getting-started.rst)
to install TinyStan's pre-requisites and downloaded a copy of the TinyStan source code.

To install the R package from the source code, run:
```R
install.packages(file.path(getwd(),"R"), repos=NULL, type="source")
```
from the TinyStan folder.

To use the TinyStan source you've manually downloaded instead of
one the package will download for you, you must use
[`set_tinystan_path()`](#function-set-tinystan-path) or the `$TINYSTAN`
environment variable.

## API Reference

### Model interface

```{include} ./_r/tinystan_model.md
```

```{include} ./_r/sampler.tinystan_model.md
```

```{include} ./_r/HMCMetric.md
:start-line: 2
```

```{include} ./_r/pathfinder.tinystan_model.md
```

```{include} ./_r/optimizer.tinystan_model.md
```

```{include} ./_r/OptimizationAlgorithm.md
:start-line: 2
```

```{include} ./_r/laplace_sampler.tinystan_model.md
```

### Compilation utilities


```{include} ./_r/set_tinystan_path.md
```


```{include} ./_r/compile_model.md
```

