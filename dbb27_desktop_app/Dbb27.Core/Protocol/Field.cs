namespace Dbb27.Core.Protocol;

public sealed record Field(
    char Id,
    string Key,
    string NameVi,
    int Size,
    string Unit,
    FieldKind Kind,
    int Decimals);
