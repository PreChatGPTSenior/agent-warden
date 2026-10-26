package lab.stoneshelter.shared;

/** A mutable response with five declared fields. */
public class DetailedResponse {
  private String id;
  private String name;
  private String kind;
  private String size;
  private String status;

  /** Returns id. */
  public String getId() {
    return id;
  }

  /** Sets id. */
  public void setId(String id) {
    this.id = id;
  }

  /** Returns name. */
  public String getName() {
    return name;
  }

  /** Sets name. */
  public void setName(String name) {
    this.name = name;
  }

  /** Returns kind. */
  public String getKind() {
    return kind;
  }

  /** Sets kind. */
  public void setKind(String kind) {
    this.kind = kind;
  }

  /** Returns size. */
  public String getSize() {
    return size;
  }

  /** Sets size. */
  public void setSize(String size) {
    this.size = size;
  }

  /** Returns status. */
  public String getStatus() {
    return status;
  }

  /** Sets status. */
  public void setStatus(String status) {
    this.status = status;
  }
}
