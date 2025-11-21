import java.util.Scanner;

public class NumberCalculator {
    // Instance variable to store the list of numbers
    private int[] numbers;
    
    // Constructor that takes an array of integers as an argument
    public NumberCalculator(int[] numbers) {
        this.numbers = numbers;
    }
    
    // Method to calculate and return the average of the numbers
    public double calculateAverage() {
        if (numbers == null || numbers.length == 0) {
            return 0.0;
        }
        
        int sum = 0;
        for (int number : numbers) {
            sum += number;
        }
        
        return (double) sum / numbers.length;
    }
    
    // Main method
    public static void main(String[] args) {
        Scanner scanner = new Scanner(System.in);
        
        // Get the number of elements from the user
        System.out.print("Enter the number of elements: ");
        int n = scanner.nextInt();
        
        // Create an array to store the numbers
        int[] numberArray = new int[n];
        
        // Take numbers from the user
        System.out.println("Enter " + n + " numbers:");
        for (int i = 0; i < n; i++) {
            System.out.print("Number " + (i + 1) + ": ");
            numberArray[i] = scanner.nextInt();
        }
        
        // Create an object of NumberCalculator class
        NumberCalculator calculator = new NumberCalculator(numberArray);
        
        // Calculate the average
        double average = calculator.calculateAverage();
        
        // Display the numbers entered
        System.out.println("\nNumbers entered:");
        for (int i = 0; i < numberArray.length; i++) {
            System.out.println("Number " + (i + 1) + ": " + numberArray[i]);
        }
        
        // Display the result
        System.out.println("\nThe average of the numbers is: " + average);
        
        scanner.close();
    }
}


