# Repository Versions

This directory contains code from several repositories that were previously included as submodules.
This file records the commit hashes of those repositories at the time they were flattened into this
repository.

## Repositories

| Repository     | Path                         | Commit Hash                                |
| :------------- | :--------------------------- | :----------------------------------------- |
| **DiskANN**    | `DiskANN/`                   | `a26f824be5a597b49a7bf33f51ee75121e7c03af` |
| **gperftools** | `third_party/gperftools/`    | `fe85bbdf4cb891a67a8e2109c1c22a33aa958c7e` |
| **GTI**        | `algorithms_impl/gti/`       | `e1232fab79d344f7f75e90aa13b2dbab2592b7a0` |
| **IP-DiskANN** | `algorithms_impl/ipdiskann/` | `c6479208a88a2cc5421b625a8af317605cc112ff` |
| **PLSH**       | `algorithms_impl/plsh/`      | `d69c8ca896e02eb80df89ba88a3f315e6e15b061` |
| **VSAG**       | `algorithms_impl/vsag/`      | `5d352a4047ddfff5fb5c2793f6b4ceb83d9e43ca` |

## Notes

- `gperftools` was originally present in both `DiskANN` and `ipdiskann`. It has been consolidated
  into `third_party/gperftools`.
