using System.Security.Cryptography;
using System.Text;

public sealed record BuildProvenance(string OwnerId, string Repository, string Release, string Sha256)
{
    public const string Owner = "gutocodes";
    public const string SourceRepository = "https://github.com/celsonaemen/LAB-AI";
    public const string ReleaseId = "bank-demo-2026.11";

    public static BuildProvenance Current()
    {
        var payload = $"{Owner}|{SourceRepository}|{ReleaseId}";
        var digest = SHA256.HashData(Encoding.UTF8.GetBytes(payload));
        return new BuildProvenance(Owner, SourceRepository, ReleaseId,
            Convert.ToHexStringLower(digest));
    }
}
