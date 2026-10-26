package lab.stoneshelter.demo;

public class EmptyCatchExample {
 public void parse(String value) {
  try { Integer.parseInt(value); } catch (NumberFormatException exception) { }
 }
}
